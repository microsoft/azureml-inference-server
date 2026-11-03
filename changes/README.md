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

Run ``python -m towncrier --draft`` from the repository root to preview the next release notes
without changing files. Run ``python -m towncrier`` when preparing a release to write the notes
to ``CHANGELOG.rst`` and remove the consumed fragments.
