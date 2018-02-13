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

### Usage

1. Example \- list all (assessible) repositories of some user:
```
$ python collector.py --host "https://github.com" -u "{user}"
```

2. Example \- retrieve anonymized, bare repository:
```
$ python collector.py -s "https://{github.hotstname}/{repo_owner}/{repo_name}" -r -a -b
```

3. Example \- retrieve set of repositories created after Jan. 01, 1970:
```
$ python collector.py -s "{repo_urls_file}" -r --since "2017-01-01"
```


## scraper.py


Generate the commit records for a set of git repositories and export this information to a data store.


| argument | type | description |
|----------|------|-------------|
| \-s, \-\-sources | string | semi\-colon\-separated list of repository paths in local working environment  \(or an input file containing the same\); Expected syntax: '' |
| \-a, \-\-anonymize | flag | apply anonymization in repository changelog data |
| \-\-paths\-in\-repo | string | comma-separated list of paths to process for all repositories |
| \-\-files\-in\-repo | string | comma-separated list of files to process for all repositories |
| \-\-data\-store | string | specify data store object |
| \-q, \-\-query | string | process only repositories containing specific tokens within their URLs |
| \-\-until | string | consider only repository commits performed before a specific date |
| \-\-since | string | consider only repository commits performed after a specific date |


### Usage

1. Example \- export repository commit information to some data store:
```
$ python scraper.py -s "{local/path/to/repo}" --data-store "{ds_object}"
```

2. Example \- export repository commit information concerning a specific path and a specific file:
```
$ python scraper.py -s "{local/path/to/repo}{?path=some_path}{&file=some_file}" --data-store "{ds_object}"
```

3. Example \- export anonymized repository commit information for any commits performed after Jan. 01, 1970:
```
$ python scraper.py -s "{local/path/to/repo}" -a --data-store "{ds_object} --since "2017-01-01"
```

4. Example \- export repository commit information concerning a particular path for some set of repositories:
```
$ python scraper.py -s "{repo_local_paths_file}" --paths-in-repo "{some_path} --data-store "{ds_object}"
```



## analyzer.py

Generate statistical information based on a set of repository commit records. Statistics correspond to a set of repository metrics and are presented in terms of frequency distribution tables \(spreadsheets files\) and distribution graphics \(HTML file\).


| argument | type | description |
|----------|------|-------------|
| \-\-data\-store | string | specify data store object |


1. Example \- generate statistics for a set of repositories stored in some data store:
```
$ python analyzer.py --data-store "{ds_object}"
```



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
