extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
]

source_suffix = [".rst"]

master_doc = "index"

project = "pyndfd"
author = "Marty J. Sullivan"
year = "2016"
copyright = "{0}, {1}".format(year, author)

version = "0.9"

release = "0.9.0"

html_theme = "sphinx_rtd_theme"
html_last_updated_fmt = "%b %d, %Y"
html_short_title = "{}-{}".format(project, version)

pygments_style = "monokai"

autodoc_member_order = "bysource"

autodoc_default_flags = ["members", "show-inheritance"]

napoleon_numpy_docstring = False

napoleon_use_ivar = True
napoleon_use_rtype = False
napoleon_use_param = False
