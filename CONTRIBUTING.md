# Contributing

This document describes the process of making a release.

## Checkout `prod`

```bash
git checkout prod
git merge --no-ff --no-edit main
```

## Update top-most `__init__.py`

Update:

```python
__version__ = "X.0.1"
```

## Update `CHANGELOG.md`

Sections order is: `Fixed`, `Changed`, `Added`, `Deprecated`, `Removed`, `Security`.

```text
---
[X.0.1]: https://github.com/metaist/freshlinks/compare/X.0.0...X.0.1

## [X.0.1] - XXXX-XX-XXT00:00:00Z

**Fixed**

**Changed**

**Added**

**Deprecated**

**Removed**

**Security**

```

## Update docs

```bash
pdm docs
```

## Check build

```bash
pip install -e .
```

## Commit & Push

```bash
git commit -am "release: X.0.1"
git tag X.0.1
git push
git push --tags
git checkout main
git merge --no-ff --no-edit prod
git push
```

## Create Release

Visit: https://github.com/metaist/freshlinks/releases/new
