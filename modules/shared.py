#!/usr/bin/python


import datetime; # Datetime handling.
import dateutil.parser as dtparser;
import hashlib; # Generate hash from string.
import os; # File, directory handling.
import pandas; # DataFrame handling.
import subprocess; # Git commands.
import urlparse; # URI parsing.
import requests; # HTTP requests.


# # Alias for '/dev/null'.
FNULL = open(os.devnull, 'w');


# Update basepath in URI path.
def add_path_to_uri(uri, path):
    
    if (uri and path):
        if (uri.endswith('/')):
            return uri + path;
        else:
            return uri + '/' + path;
    elif (uri):
        return uri;
    elif (path):
        return path;
    else:
        return '';


# Check if URI is a URL.
def is_url(uri):
    
    try:
        requests.get(uri);
        return True;
    except:
        return False;


# Check if URL refers to a GitHub repository.
def is_repo_url(url):
    
    sp = subprocess.Popen(('git ls-remote %s' % (url)), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True);
    sp.communicate();
    if (sp.returncode == 0):
        return True;
    else:
        return False;


# Check if URI is a local path.
def is_local_path(uri):
    
    if (os.path.isdir(uri)):
        return True;
    else:
        return False;


# Check if local repository is corrupt.
def is_corrupt_repo(path_to_repo):
    
    gd = '--git-dir=\'' + path_to_repo + '/.git/\'';
    wt = '--work-tree=\'' + path_to_repo + '\'';
    
    sp = subprocess.Popen(('git %s %s log' % (gd,wt)), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True);
    (log_str, _) = sp.communicate();
    
    if (log_str == "fatal: bad default revision \'HEAD\'\n" or
        log_str == "fatal: your current branch \'master\' does not have any commits yet\n"):
        return True;
    else:
        return False;


# Verify if path refers to a Git repository.
def is_repo_root(path_to_repo):
    
    if (os.path.exists(add_path_to_uri(path_to_repo, '.git'))):
        if (not is_corrupt_repo(path_to_repo)):
            return True;
        else:
            return False;
    else:
        return False;


# Get earliest-supported UTC timestamp.
def get_utc_begin_str():
    
    begin_utc = datetime.datetime(1970,1,1).strftime('%Y-%m-%dT%H:%M:%SZ');
    
    return begin_utc;


# Get UTC now timestamp.
def get_utc_now_str():
    
    now_utc = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ');
    
    return now_utc;


# Convert UTC timesamp to UNIX epoch. 
def utc_str_to_epoch(utc_dt):
    
    # ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ
    utc = datetime.datetime.strptime(utc_dt, '%Y-%m-%dT%H:%M:%SZ');
    epoch = (utc - datetime.datetime(1970,1,1)).total_seconds();
    
    return epoch;


# Split string by delimiter and tokenize.
def split_str(delimiter, input_str):
    
    tokens = list();
    
    raw_tokens = input_str.split(delimiter); # Split string by delimiter.
    
    for i in range(0, len(raw_tokens)):
        
        token = raw_tokens[i].strip(); # Prune leading or trailing space chars.
        tokens.append(token);
    
    return tokens;


# Construct repo SSH URL from repo HTTP URL.
def build_repo_ssh_url(repo_http_url):
    
    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(repo_http_url);
    
    scheme = 'ssh';
    netloc = 'git@' + netloc;
    path = path + '.git';
    
    repo_ssh_url = urlparse.urlunparse((scheme, netloc, path, params, query, fragment));
    
    return repo_ssh_url;


# Formulate user warning string.
def get_warning_str(case):
    
    warning_str = "(WARNING: " + case + " - ignoring.)";
    
    return warning_str;


# Process input file.
def process_infile(infile):
    
    with open(infile, 'r') as sources_file:
        sources = sources_file.read().replace('\n', '');
    
    return sources;


# Get repo URI and paths in repo.
# Example syntax: 'https://github.com/{username}/{reponame}=,{dirname}'.
def parse_repo_source_str(repo_source_str, process_as_url=True):
    
    paths_in_repo = list();
    files_in_repo = list();

    if (process_as_url):
        
        repo_uri = repo_source_str;

    else:
        
        parsed_uri = urlparse.urlparse(repo_source_str);

        repo_uri = parsed_uri.path;

        query_dict = urlparse.parse_qs(parsed_uri.query);
        for field in query_dict: # Fill lists, paths_in_repo and files_in_repo.

            if (field == 'path'):
                paths_in_repo = query_dict[field];
            elif (field == 'file'):
                files_in_repo = query_dict[field];
            else:
                print(get_warning_str("No such query field \'" + str(field) + "\'"));
    
    repo_source_dict = dict();
    repo_source_dict['repo_uri'] = repo_uri;
    repo_source_dict['paths_in_repo'] = paths_in_repo;
    repo_source_dict['files_in_repo'] = files_in_repo;
    
    return repo_source_dict;


# Determine if it is okay to overwrite existing file. 
def can_overwrite_file(outfile):
    
    answer = raw_input("File \'" + outfile + "\' already exists! Overwrite? [y/N] ");
    if (answer == 'y'):
        return True;
    else:
        return False;


# Check if outfile is writable.
def verify_outfile(outfile):
    
    # Case: Outfile exists.
    if (os.path.exists(outfile)): # File already exists...
        
        if (not can_overwrite_file(outfile)):
            print("Not overwriting.");
            return False;
    
    # Case: Outfile path does not exist.
    path_to_outfile = os.path.dirname(outfile); # Get outfile path.
    if (path_to_outfile): # (Outfile contained a path)...
        
        if (not os.path.isdir(path_to_outfile)): # Path does not exist...
            path_to_outfile = os.path.abspath(path_to_outfile); # Get absolute path.
            print("No such directory \'" + path_to_outfile + "\'");
            return False;
    
    # Case: Outfile is a directory.
    if (os.path.isdir(outfile) or outfile.endswith('/')): # Outfile is a directory (existing or not existing)...
        abs_path_to_outfile = os.path.abspath(outfile);
        print("Output \'" + abs_path_to_outfile + "\' is not a file.");
        return False;
    
    return True;


# Generate SHA-1 hash string for input string.
def get_hash_str(in_str):
    
    hash_obj = hashlib.sha1(in_str.encode());
    hex_digit = hash_obj.hexdigest();
    
    hash_str = str(hex_digit);
    
    return hash_str;


# Get repo remote origin URL.
def get_remote_origin_url(path_to_repo):
    
    gd = '--git-dir=\'' + path_to_repo + '/.git/\'';
    wt = '--work-tree=\'' + path_to_repo + '\'';
    
    wd = '--word-diff';
    sp = subprocess.Popen(('git %s %s config --get remote.origin.url' % (gd,wt)), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True);
    (remote_origin_url, _) = sp.communicate();
    
    remote_origin_url = remote_origin_url.strip('\n'); # Remove newline '\n'.
    
    return remote_origin_url;


# Check if text is ASCII.
def is_ascii(text):
    
    try:
        text.encode('ascii');
        return True;
    except:
        return False;


# Formulate ASCII string from text. Non-ASCII chars replaced with '?'.
def make_ascii_str(text):
    
    ascii_text = "";
    
    for c in text:
        if (is_ascii(c)):
            ascii_text = ascii_text + c;
        else:
            ascii_text = ascii_text + '?'
    
    return ascii_text;


# Formulate ASCII string from text. Non-ASCII chars replaced with '?'.
def make_ascii_str2(text):
    
    text = text.decode('utf-8');
    ascii_text = text.encode('ascii','replace');
    
    return ascii_text;


# Clone repository or just fetch its latest changes.
def update_local_repo(repo_url, directory):
    
    url_path = urlparse.urlparse(repo_url)[2];
    repo_owner = os.path.basename(os.path.abspath(os.path.join(url_path, os.pardir))); # Get name of parent directory in path.
    repo_name = os.path.basename(url_path);
    
    path_to_repo = add_path_to_uri(repo_owner, repo_name);
    abspath_to_repo = add_path_to_uri(directory, path_to_repo);
    
    clone_repo = False;
    if (not os.path.exists(abspath_to_repo)): # Local path to repo does not exist...
        os.makedirs(abspath_to_repo);
        clone_repo = True;
    elif (not is_repo_root(abspath_to_repo)): # Local path to repo is not a repo directory...
        clone_repo = True;
    
    if (clone_repo): # Clone repo...
        
        print("Cloning repo...");
        
        repo_ssh_url = build_repo_ssh_url(repo_url);
        
        sp = subprocess.Popen(('git clone %s \'%s\'' % (repo_ssh_url, abspath_to_repo)), stdout=subprocess.PIPE, shell=True);
        sp.wait();
        
    else: # ...Or just update existing repo...
        
        print("Updating repo...");
        
        gd = '--git-dir=\'' + abspath_to_repo + '/.git/\'';
        wt = '--work-tree=\'' + abspath_to_repo + '\'';
        h = '--hard HEAD';
        x = '-xffd';
        
        sp = subprocess.Popen(('git %s %s reset %s' % (gd,wt,h)), stdout=FNULL, stderr=FNULL, shell=True);
        sp.wait();
        sp = subprocess.Popen(('git %s %s clean %s' % (gd,wt,x)), stdout=FNULL, stderr=FNULL, shell=True);
        sp.wait();
        sp = subprocess.Popen(('git %s %s pull' % (gd,wt)), stdout=FNULL, stderr=FNULL, shell=True);
        sp.wait();
    
    print("Done.");
    print("Repo is at latest version.");
    
    return abspath_to_repo, repo_owner, repo_name;


# Formulate since-datetime str.
def verify_since_str(since):
    
    since_str = '';
    if (since):
        try:
            dt = dtparser.parse(since)
            since_str = datetime.datetime.strftime(dt, '%Y-%m-%dT%H:%M:%SZ')
        except:
            print(get_warning_str("Malformed since date \'" + since + "\'"));
            since_str = get_utc_begin_str();
    else:
        since_str = get_utc_begin_str();
    
    return since_str;


# Formulate until-datetime str.
def verify_until_str(until):
    
    until_str = '';
    if (until):
        try:
            dt = dtparser.parse(until)
            until_str = datetime.datetime.strftime(dt, '%Y-%m-%dT%H:%M:%SZ')
        except:
            print(get_warning_str("Malformed until date \'" + until + "\'"));
            until_str = get_utc_now_str();
    else:
        until_str = get_utc_now_str();
    
    return until_str;


# Filenames considered when processing each repo.
def verify_considered_files(files_in_repo_str):
    
    filenames = list();
    if (files_in_repo_str):
        filenames = split_str('&', files_in_repo_str);
        filenames = list(set(filenames)); # Eliminate any duplicates.
    
    return filenames;


# Paths in repo considered when processing each repo.
def verify_paths_in_repo(paths_in_repo_str):
    
    paths_in_repo = list();
    if (paths_in_repo_str):
        paths_in_repo = split_str('&', paths_in_repo_str);
        paths_in_repo = list(set(paths_in_repo)); # Eliminate any duplicates.
    
    return paths_in_repo;


# Verify working directory for runtime storage processing.
def verify_directory(directory_str):
    
    directory = '';
    if (directory_str):
        if (not os.path.exists(directory_str)): # If directory does not exists, make it.
            os.makedirs(directory_str);
        directory = os.path.abspath(directory_str);
    else:
        directory = os.getcwd(); # Use the current working directory.
    
    return directory;


# Verify repo sources (URIs and corresponding paths).
def verify_repo_sources(sources_str, include_urls=True, include_local_paths=True):
    
    if (sources_str):
        
        sources = split_str(';', sources_str); # Multiple URIs are separated by semi-colons.
        sources = list(set(sources)); # Eliminate any duplicates.
        
        valid_repos = list();
        for source in sources:
            
            sources_str = '';
            if (os.path.isfile(source)): # If input is file...
                sources_str = process_infile(source);
            else:
                sources_str = source;
            
            sources = split_str(';', sources_str); # Multiple URIs are separated by semi-colons.
            sources = list(set(sources)); # Eliminate any duplicates.
            for source_str in sources:
                
                source_dict = parse_repo_source_str(source_str, include_urls);
                uri = source_dict['repo_uri'];
                
                if (is_url(uri)):

                    if (include_urls):
                        potential_repo_ssh_url = build_repo_ssh_url(uri);
                        if (is_repo_url(potential_repo_ssh_url)):
                            if (uri not in valid_repos):
                                valid_repos.append(uri);
                        else:
                            print(get_warning_str("\'" + uri + "\' does not refer to a git repository"));
                    else:
                        print(get_warning_str("Malformed URI \'" + uri + "\'"));
                
                elif (is_local_path(uri)):

                    if (include_local_paths):
                        if (is_repo_root(uri)):
                            if (source_dict not in valid_repos):
                                valid_repos.append(source_dict);
                        else:
                            print(get_warning_str("\'" + uri + "\' does not refer to a git repository"));
                    else:
                        print(get_warning_str("Malformed URI \'" + uri + "\'"));
                
                else:
                    print(get_warning_str("Malformed URI \'" + uri + "\'"));
            
        return valid_repos;
    else:
        return list();


# Write DataFrame to file.
def write_df_to_file(df, title, outfile):
    
    df_writer = pandas.ExcelWriter(outfile);
    df.to_excel(df_writer, title, index=False);
    df_writer.save();


# Write DataFrame to file.
def write_df_to_csv(df, outfile):
    
    #df_writer = pandas.ExcelWriter(outfile);
    df.to_csv(outfile);
    #df_writer.save();


# Load data store from spreadsheet file.
def load_commit_info_data_store(data_store):
    
    try:
        ds_xls = pandas.ExcelFile(data_store); # Load spreadsheet file.
        ds_df = ds_xls.parse(); # Import spreadsheet file to DataFrame.
        #ds_df = pandas.read_html(data_store);
    except:
        return None;
    
    COLUMN_LABELS = ['repo_owner', 'repo_name', 'path_in_repo',
                     'commit_hash',
                     'author_name', 'author_email', 'author_epoch',
                     'committer_name', 'committer_email', 'committer_epoch',
                     'subject',
                     'num_files_changed',
                     'num_lines_changed', 'num_lines_inserted', 'num_lines_deleted', 'num_lines_modified'];
    
    for column_label in COLUMN_LABELS:
        
        if (column_label not in ds_df.columns):
            return None;
    
    return ds_df;


# Load data store from spreadsheet file.
def load_repo_files_data_store(data_store):
    
    try:
        ds_xls = pandas.ExcelFile(data_store); # Load spreadsheet file.
        ds_df = ds_xls.parse(); # Import spreadsheet file to DataFrame.
    except:
        return None;
    
    COLUMN_LABELS = ['repo_owner', 'repo_name',
                     'path_in_repo', 'filename',
                     'commit_hash',
                     'author_name', 'author_email', 'author_epoch',
                     'committer_name', 'committer_email', 'committer_epoch',
                     'num_lines_changed', 'num_lines_inserted', 'num_lines_deleted', 'num_lines_modified'];
    
    for column_label in COLUMN_LABELS:
        
        if (column_label not in ds_df.columns):
            return None;
    
    return ds_df;


