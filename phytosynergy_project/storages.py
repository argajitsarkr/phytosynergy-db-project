from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class StableManifestStaticFilesStorage(ManifestStaticFilesStorage):
    """ManifestStaticFilesStorage that fails soft at render time.

    Content-hashed filenames (e.g. custom.7f3a2c.css) give every static asset a
    URL that changes whenever the file's content changes, so browsers and the
    Cloudflare edge can never serve a stale copy - no manual "Purge Everything"
    after a deploy.

    manifest_strict = False means a {% static %} reference to a file that is
    missing from the manifest falls back to the un-hashed name instead of raising
    and returning a 500. Files that ARE collected still get the cache-busting hash.
    """

    manifest_strict = False
