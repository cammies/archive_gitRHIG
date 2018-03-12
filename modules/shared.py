#!/usr/bin/python


import chardet; # Detect string encoding.
import datetime; # Datetime handling.
import dateutil.parser as dtparser;
import hashlib; # Generate hash from string.
import os; # File, directory handling.
import pandas; # DataFrame handling.
import subprocess; # Git commands.
import urlparse; # URI parsing.
import requests; # HTTP requests.


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

    config = '-c color.ui=\'false\'';
    
    cmd_str = 'git %s ls-remote %s' % (config,url);
    #print(cmd_str);

    sp = subprocess.Popen(cmd_str,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          shell=True);
    
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
    
    config = '-c color.ui=\'false\'';
    gd = '--git-dir=\'' + path_to_repo + '/.git/\'';
    wt = '--work-tree=\'' + path_to_repo + '\'';
    
    cmd_str = 'git %s %s %s log' % (config,gd,wt);
    #print(cmd_str);
    
    sp = subprocess.Popen(cmd_str,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          shell=True);
    
    (gitlog_str, _) = sp.communicate();
    
    if (gitlog_str == "fatal: bad default revision \'HEAD\'\n" or
        gitlog_str == "fatal: your current branch \'master\' does not have any commits yet\n"):
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


# Determine if it is okay to overwrite existing file. 
def can_overwrite_file(dest):
    
    answer = raw_input("File \'" + dest + "\' already exists! Overwrite? [y/N] ");
    if (answer == 'y'):
        return True;
    else:
        return False;


# Check if outfile is writable.
def is_writable_file(dest):
    
    # Case: Destination already exists.
    if (os.path.exists(dest)):
        
        if (not can_overwrite_file(dest)):
            print("Not overwriting.");
            return False;
    
    # Case: Destination path does not exist.
    path_to_dest = os.path.dirname(dest); # Get destination path.
    if (path_to_dest): # If destination string contained a path...
        
        if (not os.path.isdir(path_to_dest)): # Path does not exist...
            abspath_to_dest = os.path.abspath(path_to_dest); # Get absolute path.
            print("No such directory \'" + abspath_to_dest + "\'.");
            return False;
    
    # Case: Destination is a directory.
    if (os.path.isdir(dest) or dest.endswith('/')): # Destination is a directory (existing or not existing)...
        
        abspath_to_dest = os.path.abspath(dest);
        print("Not a file \'" + abspath_to_dest + "\'.");
        return False;
    
    return True;


# Generate SHA-1 hash string for input string.
def get_hash_str(in_str):
    
    in_str = in_str.encode('utf-8', 'replace');

    hash_obj = hashlib.sha1(in_str);
    hex_digit = hash_obj.hexdigest();
    
    hash_str = str(hex_digit);
    
    return hash_str;


# Get repo remote origin URL.
def get_remote_origin_url(path_to_repo):
    
    config = '-c color.ui=\'false\'';
    gd = '--git-dir=\'' + path_to_repo + '/.git/\'';
    wt = '--work-tree=\'' + path_to_repo + '\'';
    
    wd = '--word-diff';
    
    cmd_str = 'git %s %s %s config --get remote.origin.url' % (config,gd,wt);
    #print(cmd_str);
    
    sp = subprocess.Popen(cmd_str,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          shell=True);
    
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


## Formulate ASCII string from text. Non-ASCII chars replaced with '?'.
#def make_ascii_str(text):
#    
#    ascii_text = "";
#    
#    for c in text:
#        if (is_ascii(c)):
#            ascii_text = ascii_text + c;
#        else:
#            ascii_text = ascii_text + '?'
#    
#    return ascii_text;


# Formulate UTF-8 string from text. Non-UTF-8 chars replaced with '?'.
def decode_str(text):
    
    text = text.decode('utf-8', 'replace');
    
    return text;


# Formulate since-datetime str.
def get_since_dt_str(since_dt_str):
    
    if (since_dt_str):
        try:
            dt = dtparser.parse(since_dt_str);
            since_dt_str = datetime.datetime.strftime(dt, '%Y-%m-%dT%H:%M:%SZ');
        except:
            print(get_warning_str("Malformed \'since\' date \'" + since_dt_str + "\'"));
            since_dt_str = '';#get_utc_begin_str();
    else:
        since_dt_str = '';#get_utc_begin_str();
    
    return since_dt_str;


# Formulate until-datetime str.
def get_until_dt_str(until_dt_str):
    
    if (until_dt_str):
        try:
            dt = dtparser.parse(until_dt_str);
            until_dt_str = datetime.datetime.strftime(dt, '%Y-%m-%dT%H:%M:%SZ');
        except:
            print(get_warning_str("Malformed \'until\' date \'" + until_dt_str + "\'"));
            until_dt_str = '';#get_utc_now_str();
    else:
        until_dt_str = '';#get_utc_now_str();
    
    return until_dt_str;


# Filenames considered when processing each repo.
def verify_considered_files(files_in_repo_str):
    
    filenames = list();
    if (files_in_repo_str):
        filenames = split_str('&', files_in_repo_str);
        filenames = list(set(filenames)); # Eliminate any duplicates.
    
    return filenames;


# Paths in repo considered when processing each repo.
def get_paths_in_repo(paths_in_repo_str):
    
    paths_in_repo = list();
    if (paths_in_repo_str):
        paths_in_repo = split_str(';', paths_in_repo_str);
        paths_in_repo = list(set(paths_in_repo)); # Eliminate any duplicates.
    
    return paths_in_repo;


# Paths in repo considered when processing each repo.
def get_labels(labels_str):
    
    labels = tuple();
    if (labels_str):
        labels = split_str(';', labels_str);
        labels = tuple(list(set(labels))); # Eliminate any duplicates.
    
    return labels;


# Paths in repo considered when processing each repo.
def get_intervals_dict(iwidths_str):
    
    iw_dict = dict();
    if (iwidths_str):
        iw_strs = split_str(';', iwidths_str);
        iw_strs = list(set(iw_strs)); # Eliminate any duplicates.

        for iw_str in iw_strs:
            iw = split_str(':', iw_str);
            iw_dict[iw[0]] = iw[1];
    
    return iw_dict;


# Verify working directory for runtime storage processing.
def get_wd(directory_str):
    
    if (directory_str):
        if (not os.path.exists(directory_str)): # If directory does not exists, make it.
            os.makedirs(directory_str);
        directory = os.path.abspath(directory_str);
    else:
        directory = os.getcwd(); # Use the current working directory.
    
    return directory;


# Parse local path source str.
def parse_local_path_source(source_str):
    
    source = dict();
    
    paths_in_repo = list();
    labels_for_repo = tuple();
    since_dt = list();
    until_dt = list();

    try:
        
        parsed_uri = urlparse.urlparse(source_str);

        repo_uri = parsed_uri.path;

        query_dict = urlparse.parse_qs(parsed_uri.query);
        for field in query_dict: # Get query fields...

            if (field == 'path'):
                paths_in_repo = query_dict[field];
            elif (field == 'label'):
                labels_for_repo = query_dict[field];
            elif (field == 'since'):
                since_dt = query_dict[field];
            elif (field == 'until'):
                until_dt = query_dict[field];
            else:
                print(get_warning_str("No such query field \'" + field + "\'"));
        
        source['uri'] = repo_uri;
        source['paths_in_repo'] = list(set(paths_in_repo)); # Eliminate and duplicates.
        source['labels_for_repo'] = tuple(list(set(labels_for_repo))); # Eliminate and duplicates.
        source['since'] = list(set(since_dt)); # Eliminate and duplicates.
        source['until'] = list(set(until_dt)); # Eliminate and duplicates.


    except:
        print(get_warning_str("Malformed source string \'" + source_str + "\'"));
        source['uri'] = '';
    
    return source;


# Process local path source input file.
def process_source_infile(infile):
    
    with open(infile, 'r') as sources_file:
        sources = sources_file.read().replace('\n', '');
    
    return sources;


# Return list of source dicts.
def get_local_path_sources(sources_str):

    raw_sources = split_str(';', sources_str); # Multiple URIs are semi-colon separated.
    raw_sources = list(set(raw_sources)); # Eliminate any duplicates.
    
    sources = list();
    for source in raw_sources:
        
        source_dict = parse_local_path_source(source);
        if (os.path.isfile(source_dict['uri'])): # If source is a file...
            file_sources_str = process_source_infile(source_dict['uri']); # Source str.
            sources_from_file = get_local_path_sources(file_sources_str); # Recursive call (returns list of dicts).
            for i in range (0, len(sources_from_file)):
                sources_from_file[i]['paths_in_repo'] = sources_from_file[i]['paths_in_repo'] + source_dict['paths_in_repo'];
                sources_from_file[i]['labels_for_repo'] = sources_from_file[i]['labels_for_repo'] + source_dict['labels_for_repo'];
            sources = sources + sources_from_file;
        else:
            sources.append(source_dict);

    return sources;


#
def get_repo_local_paths(sources_str):
    
    repo_local_paths = list();
    
    if (sources_str):
        
        sources = get_local_path_sources(sources_str);

        for source_dict in sources:

            uri = source_dict['uri'];
            if (is_local_path(uri)):
                        
                if (is_repo_root(uri)):
                    
                    if (source_dict not in repo_local_paths):
                        repo_local_paths.append(source_dict);
                else:
                    print(get_warning_str("\'" + uri + "\' does not refer to a git repository"));
                
            else:
                print(get_warning_str("Malformed URI \'" + uri + "\'"));

    return repo_local_paths;
 

# Return list of source dicts.
def get_url_sources(sources_str):

    sources = list();

    if (sources_str):
        
        raw_sources = split_str(';', sources_str); # Multiple URIs are semi-colon separated.
        raw_sources = list(set(raw_sources)); # Eliminate any duplicates.
        
        for source in raw_sources:
            
            if (os.path.isfile(source)): # If source is a file...
                file_sources_str = process_source_infile(source); # Source str.
                sources_from_file = get_url_sources(file_sources_str); # Recursive call (returns list of dicts).
                sources = sources + sources_from_file;
            else:
                sources.append(source);

    return sources;


#
def get_repo_urls(sources_str):
    
    sources = get_url_sources(sources_str);

    repo_urls = list();
    for source in sources:

        if (is_url(source)):
            
            if (is_repo_url(build_repo_ssh_url(source))):
                
                if (source not in repo_urls):
                    repo_urls.append(source);
            else:
                print(get_warning_str("\'" + source + "\' does not refer to a GitHub repository"));
            
        else:
            print(get_warning_str("Malformed URI \'" + source + "\'"));

    return repo_urls;
                

# Write DataFrame to file.
def write_df_to_file(df, title, destination):
    
    df_writer = pandas.ExcelWriter(destination, engine='xlsxwriter');
    df.to_excel(df_writer, title, index=False);
    df_writer.save();


# Get data store DataFrame.
def load_commits_data_store(data_store):
    
    COLUMN_LABELS = ['repo_owner', 'repo_name',
                     'path_in_repo',
                     'labels',
                     'commit_hash',
                     'author_name', 'author_email', 'author_epoch',
                     'committer_name', 'committer_email', 'committer_epoch',
                     'subject', 'len_subject',
                     'num_files_changed',
                     'num_lines_changed', 'num_lines_inserted', 'num_lines_deleted', 'num_lines_modified'];

    try:
        
        ds_xlsx = pandas.ExcelFile(data_store); # Load spreadsheet file.
        ds_df = ds_xlsx.parse(); # Import data store to DataFrame.
        
        for column_label in COLUMN_LABELS: # Ensure each column name in DataFrame is what is expected in commits data store...
            
            if (column_label not in ds_df.columns):
                return None;
        
        return ds_df;
    
    except:
        return None;


# Load data store from spreadsheet file.
def load_repo_files_data_store(data_store):
    
    COLUMN_LABELS = ['repo_owner', 'repo_name',
                     'path_in_repo', 'filename',
                     'labels',
                     'commit_hash',
                     'author_name', 'author_email', 'author_epoch',
                     'committer_name', 'committer_email', 'committer_epoch',
                     'num_lines_changed', 'num_lines_inserted', 'num_lines_deleted', 'num_lines_modified'];
    
    try:
        
        ds_xlsx = pandas.ExcelFile(data_store); # Load spreadsheet file.
        ds_df = ds_xlsx.parse(); # Import spreadsheet file to DataFrame.
        
        for column_label in COLUMN_LABELS:
            
            if (column_label not in ds_df.columns):
                return None;
            
        return ds_df;
    
    except:
        return None;


