from urllib2 import urlopen, HTTPError
from contextlib import closing
import os
import re
import subprocess
import mimetypes

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import Http404, HttpResponse
from django.utils import simplejson, html, encoding
from django.conf import settings

base_dir = os.path.join(settings.PROJECT_DIR, "media", "master")
git_dir = os.path.join(base_dir, ".git")

def call_git(command):
    return subprocess.call(["git", "--git-dir", git_dir, "--work-tree", base_dir] + command)

def output_git(command):
    return subprocess.check_output(["git", "--git-dir", git_dir, "--work-tree", base_dir] + command)

def blob_or_tree(user, branch, path):
    return output_git(["ls-tree", "refs/remotes/" + user + "/" + branch, path]).split(None, 3)[1]

def dirserve(request, branch="", path=""):
    if ":" in branch:
        user, branch = branch.split(":")
    else:
        user = 'origin'

    if call_git(["show-ref", "--verify", "--quiet", "refs/remotes/" + user + "/" + branch]):
        raise Http404

    file_list = output_git(["ls-tree", "-z", user + "/" + branch + ":" + path])

    file_list = file_list.strip('\0').split('\0')

    files = []

    for f in file_list:
        _, blob_or_tree, _, name = f.split(None)

        if blob_or_tree == 'tree':
            name += '/'

        files.append(name)

    if path:
        files.insert(0, "..")

    files = ['<a href="%s">%s</a><br>' % (f, f)
             for f in files]

    output = ["<h1>Directory for <strong>" + user + ":" + branch + "/" + path + "%s</strong></h1>" % ("" if path == "" else "/")] + files

    return HttpResponse(output)

def fileserve(request, branch="", path=""):
    if ":" in branch:
        user, branch = branch.split(":")
    else:
        user = 'origin'

    if call_git(["show-ref", "--verify", "--quiet", "refs/remotes/" + user + "/" + branch]):
        raise Http404

    if blob_or_tree(user, branch, path) == "tree":
        return dirserve(request, user + ":" + branch, path)

    file = output_git(["show", user + "/" + branch + ":" + path])
    type = mimetypes.guess_type(request.path)[0]

    return HttpResponse(file, content_type=type)

def home(request):
    call_git(["fetch", "-p", "origin"])

    branch_prefix = "refs/remotes/origin/"
    branch_list = output_git(["for-each-ref", "--format=%(refname)", branch_prefix + "*"])

    branch_list = branch_list.strip().split("\n")

    branches = []

    for branch in branch_list:
        if not branch.startswith(branch_prefix):
            raise Exception("Branch %r doesn't start with %r" % (branch, branch_prefix))

        branch = branch[len(branch_prefix):]

        if branch == "HEAD":
            continue

        branches.append({
            'name': branch,
        })

    branches.sort(key=lambda b: b['name'])

    with closing(urlopen("https://api.github.com/repos/%s/%s/pulls?per_page=100" % (settings.SANDCASTLE_USER, settings.SANDCASTLE_REPO))) as u:
        pull_data = u.read()

    arc_process = subprocess.Popen(["arc", "call-conduit", "differential.query"], shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True)
    phab_data = arc_process.communicate('{"status": "status-open"}')[0]

    pulls = simplejson.loads(pull_data)
    phabs = simplejson.loads(phab_data)

    context = {
        'pulls': pulls,
        'branches': branches,
        'phabs': phabs,
    }

    return render_to_response(
        "home.html",
        context,
        context_instance = RequestContext(request),
    )

def render_diff(request, title, body, patch, user, branch):
    name = "%s:%s" % (user, branch)
    castle = "/castles/%s" % name

    patch = html.escape(patch)
    r_filename = re.compile(r'(?<=^\+\+\+ b/)(.+)$', re.MULTILINE)
    all_files = r_filename.findall(patch)
    patch = r_filename.sub(r'<a href="%s/\1">\1</a>' % castle, patch, 0)
    patch_linked = html.mark_safe(patch)

    context = {
        'title': title,
        'body': body,
        'patch': patch_linked,
        'all_files': all_files,
        'castle': castle,
        'branch': name,
    }

    return render_to_response(
        'diff.html',
        context,
        context_instance = RequestContext(request),
    )

def phab(request, id=None):

    return ""

def pull(request, number=None):
    user = settings.SANDCASTLE_USER

    try:
        with closing(urlopen("https://api.github.com/repos/%s/%s/pulls/%s" % (settings.SANDCASTLE_USER, settings.SANDCASTLE_REPO, number))) as u:
            pull_data = u.read()
    except HTTPError:
        raise Http404
    pull_data = simplejson.loads(pull_data)
    user, branch = pull_data['head']['label'].split(":")

    call_git(["remote", "add", user, "git://github.com/%s/%s.git" % (user, settings.SANDCASTLE_REPO)])
    call_git(["fetch", user])

    with closing(urlopen(pull_data['diff_url'])) as u:
        patch = encoding.force_unicode(u.read(), errors='ignore')

    return render_diff(request, pull_data['title'], pull_data['body'], patch, user, branch)

def branch(request, branch=None):
    user = settings.SANDCASTLE_USER

    title = branch

    if ":" in branch:
        user, branch = branch.split(":")
    else:
        user = "origin"

    call_git(["remote", "add", user, "git://github.com/%s/%s.git" % (user, settings.SANDCASTLE_REPO)])
    call_git(["fetch", user])

    patch = output_git(["diff", "refs/remotes/origin/master...refs/remotes/" + user + "/" + branch])

    return render_diff(request, title, "", patch, user, branch)
