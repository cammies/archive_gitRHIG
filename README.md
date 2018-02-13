# gitDIGR Toolset


# Description
gitDIGR (for **git** **D**evelopment **I**nformation **G**rabber for **R**epositories) is a toolset for collecting, scraping, and analyzing commit log information for a set of git repositores. The framework consists of Python scripts that are designed to assist with processes pertaining to mining git repositories to obtain information and insights on repository commit activity and events.


## collector.py

List or batch-retrieve the \(visible\) repositories of some GitHub user.

| argument | type | description |
|----------|------|-------------|
| \-s, \-\-sources | string | semi\-colon\-separated list of repository URLs \(or an input file containing the same\) |
| \-\-host | string | HTTPS GitHub hostname |
| \-p, \-\-password | flag | prompt for GitHub username and password |
| \-t, \-\-token | flag | prompt for GitHub access token |
| \-u, \-\-username | string | process repos of a specific GitHub user |
| \-q, \-\-query | string | process only repositories containing specific tokens within their URLs |
| \-\-until | string | process only repositories modified before a specific date |
| \-\-since | string | process only repositories created after a specific date |
| \-r, \-\-retrieve | flag | clone repositories |
| \-a, \-\-anonymize | flag | apply anonymization in repository changelog data |
| \-b, \-\-bare | flag | reitrieve bare repositories when cloning |
| \-d, \-\-directory | string | runtime working directory |
| \-o, \-\-outfile | string | output file containing semi\-colon\-separated list paths of cloned repository paths in local working environment |


## scraper.py

Generate the commit records for a set of git repositories and export this information to a data store.

| argument | type | description |
|----------|------|-------------|
| \-s, \-\-sources | string | semi\-colon\-separated list of repository paths in local working environment  \(or an input file containing the same\) |
| \-a, \-\-anonymize | flag | apply anonymization in repository changelog data |
| \-\-paths\-in\-repo | string | comma-separated list of paths to process in repositories |
| \-\-files\-in\-repo | string | comma-separated list of files to process in repositories |
| \-\-data\-store | string | specify data store object |
| \-q, \-\-query | string | process only repositories containing specific tokens within their URLs |
| \-\-until | string | consider only repository commits performed before a specific date |
| \-\-since | string | consider only repository commits performed after a specific date |


## analyzer.py

Generate statistical information based on a set of repository commit records. Statistics correspond to a set of repository metrics and are presented in terms of frequency distribution tables \(spreadsheets files\) and distribution graphics \(HTML file\).

| argument | type | description |
|----------|------|-------------|
| \-\-data\-store | string | specify data store object |


## Required Python Modules
- argparse
- bokeh
- collections
- datetime
- getpass
- io
- numpy
- os
- pandas
- re
- requests
- subprocess
- sys
- textwrap
- time
- urlparse

