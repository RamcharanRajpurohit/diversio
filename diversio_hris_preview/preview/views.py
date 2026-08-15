from types import SimpleNamespace

from django.core.paginator import Paginator
from django.shortcuts import redirect, render

from .core.analyzer import analyze
from .core.models import CSVFormatError
from .forms import UploadForm
from .result_cache import get as get_cached_preview
from .result_cache import put as cache_preview

PAGE_SIZE = 100


def _page_url(request, page_param: str, page_number: int) -> str:
    query = request.GET.copy()
    query[page_param] = page_number
    return f"{request.path}?{query.urlencode()}"


def _paginate(request, rows, page_param: str) -> SimpleNamespace:
    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get(page_param))
    return SimpleNamespace(
        rows=page.object_list,
        total=len(rows),
        page=page,
        prev_url=_page_url(request, page_param, page.previous_page_number())
        if page.has_previous()
        else "",
        next_url=_page_url(request, page_param, page.next_page_number())
        if page.has_next()
        else "",
    )


def import_preview(request):
    """Show the upload form, or the preview for a posted file."""
    if request.method != "POST":
        token = request.GET.get("token")
        if token:
            cached = get_cached_preview(token)
            if cached:
                return _render_result(request, cached.filename, cached.result)
            return render(
                request,
                "preview/upload.html",
                {
                    "form": UploadForm(),
                    "file_error": "That preview expired. Upload the CSV again.",
                    "filename": "The previous upload",
                },
                status=404,
            )
        return render(request, "preview/upload.html", {"form": UploadForm()})

    form = UploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, "preview/upload.html", {"form": form}, status=400)

    upload = form.cleaned_data["csv_file"]
    try:
        # .file is the underlying binary handle: BytesIO for a small upload,
        # a temporary file on disk for anything over 2.5 MB. Passing the handle
        # rather than .read() keeps both paths identical and avoids pulling a
        # large export into memory twice.
        result = analyze(upload.file, top_managers=None)
    except CSVFormatError as error:
        return render(
            request,
            "preview/upload.html",
            {"form": UploadForm(), "file_error": str(error), "filename": upload.name},
            status=400,
        )

    token = cache_preview(upload.name, result)
    return redirect(f"{request.path}?token={token}")


def _render_result(request, filename, result):
    return render(
        request,
        "preview/result.html",
        {
            "result": result,
            "filename": filename,
            "identity_errors_page": _paginate(
                request, result.identity_errors, "identity_errors_page"
            ),
            "manager_errors_page": _paginate(
                request, result.manager_errors, "manager_errors_page"
            ),
            "roots_page": _paginate(request, result.roots, "roots_page"),
            "managers_page": _paginate(request, result.managers, "managers_page"),
            "cycles_page": _paginate(
                request, result.cyclic_employees, "cycles_page"
            ),
        },
    )
