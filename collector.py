#!/usr/bin/python


import argparse; # Script arguments
import datetime; # Timestamp handling
import getpass; # Get user input without echo
import hashlib; # Generate hash from string
import json; # Output format
import modules.shared as sh;
import os; # File, directory handling 
import re; # Regular expressions
import requests; # HTTP requests
import subprocess; # Git
import sys; # Script termination
import time; # Timestamp handling
import urlparse; # URL parsing


# Global variables.

args = ''; # For script arguments object.

session = requests.Session(); # Session (used to make authenticated GitHub web requests.

github_api_url = ''; # Github API URL.

# GitHub user authentication variables.
username = ''; # Username.
password = ''; # Password.
access_token = ''; # Personal access token.
#... # OAuth credentials.

authenticated_user = ''; # Authenticated user GitHub username.


# Process script arguments.
def process_args():
    
    argparser = argparse.ArgumentParser();
    
    argparser.add_argument('-s','--sources', help="semi-colon-separated list of repo URIs (i.e., URL, local path or input file)", type=str);
    argparser.add_argument('--host', help="HTTPS GitHub hostname", type=str);
    argparser.add_argument('-p','--password', help="prompt for GitHub username and password", action="store_true");
    argparser.add_argument('-t','--token', help="prompt for GitHub access token", action="store_true");
    #argparser.add_argument('-a','--oauth', help="prompt for GitHub OAuth credentials", action="store_true");
    argparser.add_argument('-u','--username', help="process repos of a specific GitHub user", type=str);
    argparser.add_argument('-d','--directory', help="runtime working directory", type=str);
    argparser.add_argument('-o','--outfile', help="output file for local repo paths", type=str);
    #argparser.add_argument('-q','--query', help="process only repos with specific words in their names", type=str);
    argparser.add_argument('-q','--query', help="process only repos with key words in URL", type=str);
    argparser.add_argument('-r','--retrieve', help="clone repos to local machine", action="store_true");
    argparser.add_argument('-b','--bare', help="clone bare repos to local machine", action="store_true");
    argparser.add_argument('-a','--anonymize', help="anonymize repo info in data store", action="store_true");
    argparser.add_argument('--since', help="scrape only commits after a specific date", type=str);
    argparser.add_argument('--until', help="scrape only commits before a specific date", type=str);
    
    return argparser.parse_args();


# Verify GitHub authentication credentials have been provided.
def auth_provided():

    if (args.password):
        return True;
    elif (args.token):
        return True;
    #elif (args.oauth):
        # return True;

    return False;


# Construct GitHub API repo URL from its HTTPS repo URL.
def build_github_api_url(github_host_url):
    
    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(github_host_url);
    
    if (netloc == 'github.com'): # GitHub.com URL
        netloc = 'api.' + netloc;
    else: # GitHub Enterprise URL
        path = 'api/v3';
    
    github_api_url = urlparse.urlunparse((scheme, netloc, path, params, query, fragment));
    
    return github_api_url;


# Validate user GitHub authentication.
def valid_auth(github_api_url):

    if (args.password):
        auth_type = 'username/password';
        request = requests.get(github_api_url, auth=(username, password));
    elif (args.token):
        auth_type = 'access token';
        request = requests.get(github_api_url, headers={'Authorization': 'token %s' % access_token});
    #elif (args.oauth):
        # global ...
        # auth_type = 'OAuth';
        # request = requests.get(github_api_url, ...);

    try:
        request.raise_for_status(); # Request did not raise status code 4xx or 5xx.
        return True;
    except:
        print("Invalid " + auth_type + ".");
        return False;


# Retrieve user GitHub authentication credentials.
def authenticate(github_api_url):

    while (True):
        
        if (args.password):
            global username;
            global password;
            username = raw_input("Username for \'" + args.host + "\': ");
            password = getpass.getpass("Password for \'" + args.host + "\': ");
        elif (args.token):
            global access_token;
            access_token = getpass.getpass("Access token for \'" + args.host + "\': ");
        #elif (args.oauth):
            # ... (Code to support OAuth credentials)
        
        if (valid_auth(github_api_url)):
            print("Authentication successful.");
            return True;
        else:
            print("Authentication failed!");
            again = raw_input("Try again? [y/N] ");
            if (again == 'y'):
                pass;
            else:
                return False;


# Authenicate HTTP session using user GitHub authentication credentials.
# (Session object is used to make GitHub API requests, which requires authentication.)
def authenticate_session():
    
    global session;

    if (args.password): # Basic (username and password)
        global username;
        global password;
        session.auth = (username, password);
    elif (args.token): # Personal access token
        global access_token;
        session.headers.update({'Authorization': 'token %s' % access_token});
    #elif (args.oauth1): # OAuth
    #    session.auth = OAuth1(app_key, app_secret, oauth_token, oauth_token_secret);


# Reset session authentication variables.
def scrub_credentials_info():
   
    global session;
    global username;
    global password;
    global access_token;
    # OAuth variables

    session = '';
    username = '';
    password = '';
    access_token = '';
    # Scrub OAuth variables


#
def good_github_host(github_api_url):

    if (sh.is_url(github_api_url)):

        response = requests.get(github_api_url);

        if ('current_user_url' in response.content): # Check if response contains expected content for this type of API request.
            return True;
        else:
            return False

    else:
        return False;


#
def get_authenticated_user(github_api_url):

    github_user_api_url = github_api_url + '/user';

    response = session.get(github_user_api_url);
    
    user = json.loads(response.content);

    username = user['login'];
    
    return username;


# Check script arguments.
def check_args():
    
    print("Checking script arguments...");
    
    # GitHub host URL.
    if (args.host):
        if (not auth_provided()):
            print("Must specify authentication prompt!");
            sys.exit();
        global github_api_url;
        github_api_url = build_github_api_url(args.host);
        #if (good_github_host(github_api_url)):
        if (authenticate(github_api_url)):
            authenticate_session();
        else:
            print("Authentication is required.");
            sys.exit();
        #else:
        #    print("Bad GitHub host \'" + args.host + "\'.");
        #    sys.exit();
    elif (not args.host and not args.sources):
        print("Must provide either a GitHub host URL or repo URLs.");
        sys.exit();
    
    # Repo sources (URIs and corresponding paths).
    args.sources = sh.get_repo_urls(args.sources);
    
    # Working directory.
    args.directory = sh.get_wd(args.directory);
    
    # Output file.
    if (args.outfile):
        if (not sh.is_writable_file(args.outfile)):
            sys.exit();
    #else: # Default output filename...
    #    args.outfile = 'collected-repo-local-paths_' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S%f')[:-3] + '.txt';

    #args.query = (args.query).split();
    
    # 'Since' datetime string.
    since_dt_str = sh.get_since_dt_str(args.since);
    args.since = since_dt_str if since_dt_str else sh.get_utc_begin_str();
    
    # 'Until' datetime string.
    until_dt_str = sh.get_until_dt_str(args.until);
    args.until = until_dt_str if until_dt_str else sh.get_utc_now_str();
    

# Print script argument configurations.
def echo_args():
   
    user = '';
    #if (args.username):
    #    global github_api_url;
    #    user = args.username if args.username else get_authenticated_user(github_api_url);

    print("USER: " + str(user));
    #print("QUERY: \'" + str(args.query) + "\'");
    print("SINCE: " + str(args.since));
    print("UNTIL: " + str(args.until));


# Construct GitHub API user repos URL from its HTTPS hostname.
def build_user_repos_api_url(github_api_url):

    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(github_api_url);
    
    if (args.username):
        path = path + '/users/' + args.username + '/repos';
    else:
        path = path + '/user/repos';
    
    user_repos_api_url = urlparse.urlunparse((scheme, netloc, path, params, query, fragment));
    
    return user_repos_api_url;


# Obtain a list of user repo SSH URLs.
def get_user_repo_html_urls(user_repos_api_url):
    
    since_epoch = float(sh.utc_str_to_epoch(args.since));
    until_epoch = float(sh.utc_str_to_epoch(args.until));

    repo_html_urls = list();
    max_records_per_page = 100;
    page_num = 1;
    last_page = False;
    while (not last_page):
        
        response = session.get(user_repos_api_url, params={'per_page': max_records_per_page, 'page': page_num});

        if (len(response.content) > len('[]')):
            
            repos_info = json.loads(response.content);

            for repo in repos_info:

                created_at_epoch = sh.utc_str_to_epoch(repo['created_at']);
                pushed_at_epoch = sh.utc_str_to_epoch(repo['pushed_at']);

                if (created_at_epoch >= since_epoch and pushed_at_epoch <= until_epoch):
                    repo_html_urls.append(str(repo['html_url']));
            
            page_num = page_num + 1;
        
        else: 
            last_page = True;
    
    return repo_html_urls;


# Return list of repos where query str appears in repo URL.
def find_repos(repo_urls, match_str):
    
    match_words = match_str.split('\s+'); # Split query str by '\s' char(s).

    matched_repo_urls = list();
    for repo_url in repo_urls:

        matched_all = all(mw.lower() in repo_url.lower() for mw in match_words); # True if all query tokens found in repo URL; else False.
        if (matched_all):
            matched_repo_urls.append(repo_url);
        
    return matched_repo_urls;


# Construct Git SSH repo URL from its HTTPS repo URL.
def get_repo_ssh_url(repo_url):
    
    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(repo_url);
    
    scheme = 'ssh';
    netloc = 'git@' + netloc;
    path = path + '.git';
    
    repo_ssh_url = urlparse.urlunparse((scheme, netloc, path, params, query, fragment));
    
    return repo_ssh_url;


# Determine whether or not repo is bare.
def is_bare_repo(path_to_repo):
    
    gd = '--git-dir=\'' + path_to_repo + '/.git/\'';
    ibr = '--is-bare-repository';

    cmd_str = 'git %s rev-parse %s' % (gd,ibr);
    #print(cmd_str);

    sp = subprocess.Popen(cmd_str,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          shell=True);
    
    (gitrevparse_str, _) = sp.communicate();
    
    bool_val = gitrevparse_str.strip();
    if (bool_val == 'true'):
        return True;
    else:
        return False;


# Clone repository or just fetch its latest changes.
def update_local_repo(repo_url):
    
    url_path = urlparse.urlparse(repo_url)[2];
    repo_owner = os.path.basename(os.path.abspath(os.path.join(url_path, os.pardir))); # Get name of parent directory in path.
    repo_name = os.path.basename(url_path);

    if (args.anonymize):
        repo_owner = sh.get_hash_str(repo_owner);
        repo_name = sh.get_hash_str(repo_name);
    
    path_to_repo = sh.add_path_to_uri(repo_owner, repo_name);
    abspath_to_repo = sh.add_path_to_uri(args.directory, path_to_repo);
    
    clone_repo = False;
    if (not os.path.exists(abspath_to_repo)): # Local path to repo does not exist...
        os.makedirs(abspath_to_repo);
        clone_repo = True;
    elif (not sh.is_repo_root(abspath_to_repo)): # Local path to repo is not a repo directory...
        clone_repo = True;
    
    url = get_repo_ssh_url(repo_url);
    
    if (clone_repo): # Clone repo...
        
        print("Cloning repo...");
        
        if (args.bare):
            
            b = '--bare';
            p = '\'' + abspath_to_repo + '/.git/\'';

            cmd_str = 'git clone %s %s %s' % (b,url,p);
            #print(cmd_str);

            sp = subprocess.Popen(cmd_str,
                                  stdout=subprocess.PIPE,
                                  #stderr=subprocess.STDOUT,
                                  shell=True);
            sp.wait();
        
        else:
            
            p = '\'' + abspath_to_repo + '\'';
            
            cmd_str = 'git clone %s %s' % (url,p);
            #print(cmd_str);
            
            sp = subprocess.Popen(cmd_str,
                                  stdout=subprocess.PIPE,
                                  #stderr=subprocess.STDOUT,
                                  shell=True);
            
            sp.wait();
        
    else: # ...Or just update existing repo...
   
        
        bare = is_bare_repo(abspath_to_repo);
        
        gd = '--git-dir=\'' + abspath_to_repo + '/.git/\'';
        
        if (bare):
            
            print("Updating bare repo...");

            q = '-q origin';

            cmd_str = 'git %s fetch %s master:master' % (gd,q);
            #print(cmd_str);
            
            sp = subprocess.Popen(cmd_str,
                                  stdout=subprocess.PIPE,
                                  #stderr=subprocess.STDOUT,
                                  shell=True);
            
            sp.wait();
        
        else:
            
            print("Updating repo...");
            
            wt = '--work-tree=\'' + abspath_to_repo + '\'';
            h = '--hard HEAD';
            x = '-xffd';
            
            cmd_str = 'git %s %s reset %s' % (gd,wt,h);
            #print(cmd_str);

            sp = subprocess.Popen(cmd_str,
                                  stdout=subprocess.PIPE,
                                  #stderr=subprocess.STDOUT,
                                  shell=True);
            
            sp.wait();
            
            cmd_str = 'git %s %s clean %s' % (gd,wt,x);
            #print(cmd_str);
            
            sp = subprocess.Popen(cmd_str,
                                  stdout=subprocess.PIPE,
                                  #stderr=subprocess.STDOUT,
                                  shell=True);
            
            sp.wait();
            
            cmd_str = 'git %s %s pull' % (gd,wt);
            #print(cmd_str);
            
            sp = subprocess.Popen(cmd_str,
                                  stdout=subprocess.PIPE,
                                  #stderr=subprocess.STDOUT,
                                  shell=True);
            
            sp.wait();
    
    print("Done.");
    print("Repo is at latest version.");
    
    return abspath_to_repo;


# Write list of repo local paths to file.
def write_repo_paths_to_file(repo_local_paths):

    outfile = open(args.outfile, 'w');
    outfile.write(';\n'.join(repo_local_paths));
    outfile.close();

    print("List of repo local paths saved to \'" + args.outfile + "\'.");


# Driver for collector.
def main():

    global args;
    global github_api_url;

    args = process_args();

    print('');
    check_args();
    print('');
    echo_args();

    repo_urls = list();

    if (args.host):
        user_repos_api_url = build_user_repos_api_url(github_api_url);
        repo_urls = get_user_repo_html_urls(user_repos_api_url);
    
    repo_urls = repo_urls + args.sources;
    if (args.query):
        repo_urls = find_repos(repo_urls, args.query);

    start = datetime.datetime.now();
    if (repo_urls): # Ensure list is not empty...
        
        if (args.retrieve):
            
            download_paths = list();
            num_repos = len(repo_urls);
            for i in range(0, len(repo_urls)):
               
                repo_url = repo_urls[i]
                print('');
                print("Processing repository " + str(i+1) + " of " + str(num_repos) + "...");
                print("URL: " + str(repo_url));
                repo_local_path = update_local_repo(repo_url);
                download_paths.append(repo_local_path);

            if (args.outfile):
                print('');
                write_repo_paths_to_file(download_paths);

        elif (repo_urls):
            
            print('');
            print("REPO_URLS:");
            for i in range(0, len(repo_urls)):
                print(repo_urls[i]);

    #else:
    #    print("(No repos found containing \'" + query + "\')");

    scrub_credentials_info();
    
    end = datetime.datetime.now();
    elapsed_time = end - start;
    print('');
    print("Elapsed Time: " + str(elapsed_time));
    print("Execution Complete.");
    
    return;


main();
