# gitRHIG Toolset


# Description
gitRHIG (for **git** **R**epository **H**istory **I**nformation **G**rabber) is a toolset for collecting, scraping, and analyzing the changelog information observable in a set of [git](https://git-scm.com/) repositores. The gitRHIG framework consists of Python scripts that are designed to assist with tasks oriented toward mining git repositories to obtain information and insights on repository commit activity and events.


## collector

List or batch-retrieve the repositories associated with a particular [GitHub](https://github.com/) user account.

| argument | type | description |
|----------|------|-------------|
| \-s, \-\-sources | string | semi\-colon\-separated list of repository URLs, or an input text file containing the same |
| \-\-host | string | HTTPS GitHub hostname |
| \-p, \-\-password | flag | prompt for GitHub username and password |
| \-t, \-\-token | flag | prompt for GitHub access token |
| \-u, \-\-username | string | process repositories associated with the specified GitHub user |
| \-q, \-\-query | string | process only repositories containing particular tokens in their URL text |
| \-\-until | string | process only repositories modified before a particular date |
| \-\-since | string | process only repositories created after a particular date |
| \-r, \-\-retrieve | flag | clone repositories |
| \-a, \-\-anonymize | flag | apply anonymization on cloned repository paths |
| \-b, \-\-bare | flag | opt for bare repositories when cloning |
| \-d, \-\-directory | string | runtime working directory for cloned repositores |
| \-o, \-\-outfile | string | output file containing semi\-colon\-separated list of cloned repository paths relative to local working environment |

### Examples

**1.** List all (accessible) repository HTTPS URLs associated with particular GitHub user:
```
$ python collector.py --host https://github.com -u {user} -p
```

**2.** Retrieve an anonymized, bare repository:
```
$ python collector.py -s https://{github.hostname}/{repository_owner}/{repository_name} -r -a -b
```

**3.** Retrieve some set of repositories created after Jan. 01, 1970:
```
$ python collector.py -s {repository_urls_list_file} -r --since 1970-01-01
```



## scraper

Obtain commit history information for a set of git repositories in tabular format and export the resulting records to a data store.

| argument | type | description |
|----------|------|-------------|
| \-s, \-\-sources | string | semi\-colon\-separated list of repository paths \(relative to local working environment\), or an input text file containing the same |
| \-a, \-\-anonymize | flag | apply anonymization on resulting repository commit records |
| \-\-paths\-in\-repo | string | comma-separated list of paths to process relative to all repositories |
| \-\-files\-in\-repo | string | comma-separated list of files to process relative to all repositories |
| \-\-data\-store | string | specify data store object |
| \-\-until | string | consider only repository commits performed before a particular date |
| \-\-since | string | consider only repository commits performed after a particular date |

### Examples

**1.** Export repository commit information to some data store:
```
$ python scraper.py -s {relative/path/to/repository} --data-store {ds_object}
```

**2.** Export repository commit information concerning a specific path and a specific file:
```
$ python scraper.py -s {relative/path/to/repository}{?}{path=path_1}{&}{file=file_1} --data-store {ds_object}
```

**3.** Export anonymized repository commit information for any commits performed after Jan. 01, 1970:
```
$ python scraper.py -s {relative/path/to/repository} -a --data-store {ds_object} --since 1970-01-01
```

**4.** Export repository commit information concerning particular paths for some set of repositories:
```
$ python scraper.py -s {relative/path/to/repository} --paths-in-repo {path_1, path_2,..., path_n} --data-store {ds_object}
```



## analyzer

Generate statistical information based on a set of repository commit records. This information corresponds to a set of repository metrics \(based on attributes observable in revision history\), and are presented as frequency distribution tables \(spreadsheets files\) and distribution graphics \(HTML file\).

| argument | type | description |
|----------|------|-------------|
| \-\-data\-store | string | specify data store object |

### Examples

**1.** Generate repository statistics for a set of commit records accessible in some data store:
```
$ python analyzer.py --data-store {ds_object}
```



# Requirements

## Python Modules:
- argparse
- ast
- [bokeh](https://pypi.python.org/pypi/bokeh)\*
- collections
- datetime
- [dateutil](https://pypi.python.org/pypi/python-dateutil/)\*
- getpass
- hashlib
- io
- json
- math
- [numpy](https://pypi.python.org/pypi/numpy)\*
- os
- [pandas](https://pypi.python.org/pypi/pandas)\*
- re
- [requests](https://pypi.python.org/pypi/requests)\*
- subprocess
- sys
- textwrap
- time
- urlparse
- \*[xlwt](https://pypi.python.org/pypi/xlwt)\*
- \*[openpyxl](https://pypi.python.org/pypi/openpyxl)\*
- [xlswriter](https://pypi.python.org/pypi/XlsxWriter/)\*

\* May require install

## Environment Setup:
- [Create a GitHub user account](https://github.com/join)
- [Configure GitHub account with SSH \(Secure Shell\)](https://help.github.com/articles/connecting-to-github-with-ssh/)
