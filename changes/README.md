This directory contains the change logs for each change to this package. These reStructuredText-formatted text files
will then be merged into ``CHANGELOG.rst`` before each release with [towncrier]( https://github.com/twisted/towncrier).

These change log files should be named ``<work item or pull request id>.<category>.rst``, where
the id identifies the Azure DevOps work item or GitHub pull request and ``<category>`` is one of:

* ``feature``: a new feature
* ``enhancement``: an improvement of existing functionality
* ``fix``: a bug fix.
* ``breaking``: a breaking change

Towncrier reads these fragments, not Git history or existing entries in ``CHANGELOG.rst``.
For changes awaiting release, add a fragment here instead of editing an ``Unreleased`` section
in ``CHANGELOG.rst``.
Each change since the previous release needs a new fragment; changing the version alone
does not create release notes. Fragments consumed by a previous release are not reused.
For changes without a work item or pull request number, use a name such as
``+towncrier.fix.rst``.

Install the project's release tooling with ``python -m pip install ".[dev]"``.
Use the Towncrier version specified there rather than an older installation that depends on
the deprecated ``pkg_resources`` API.
The draft version is read directly from ``azureml_inference_server_http/_version.py``,
so version edits do not require reinstalling the package.

Run ``python -m towncrier --draft`` from the repository root to preview the next release notes
without changing files. Run ``python -m towncrier`` when preparing a release to write the notes
to ``CHANGELOG.rst`` and remove the consumed fragments.
