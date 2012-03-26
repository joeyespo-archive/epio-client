import os
import subprocess
import tempfile
import platform
import shutil
from epio.commands import AppNameCommand, CommandError

class Command(AppNameCommand):
    help = 'Uploads the current directory as an app.'
    
    def handle_app_name(self, app, **options):
        is_windows = 'Windows' in platform.platform()
        # Make sure they have git
        git = None
        try:
            subprocess.call(["git"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            git = "git"
        except OSError:
            if is_windows:
                try:
                    subprocess.call(["git.cmd"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    git = "git.cmd"
                except OSError:
                    pass
        if git is None:
            raise CommandError("You must install git before you can use epio upload.")
        
        print "Uploading %s as app %s" % (os.path.abspath("."), app)
        # Make a temporary git repo, commit the current directory to it, and push
        temp_dir = tempfile.mkdtemp(prefix="epio-upload-")
        if is_windows and not os.environ.has_key('HOME'):
            os.environ['HOME'] = os.environ['USERPROFILE'] #failsafe HOME
        try:
            # Copy the files across
            repo_dir = os.path.join(temp_dir, 'repo')
            shutil.copytree('.', repo_dir)
            # Remove any old git repos (including submodules)
            env = dict(os.environ)
            for search_dir in os.walk(repo_dir, topdown=False):
                dirpath, dirnames, filenames = search_dir
                if os.path.basename(dirpath) == '.git':
                    shutil.rmtree(dirpath, ignore_errors=True)
            # Init the git repo
            subprocess.Popen(
                [git, "init"],
                env=env,
                stdout=subprocess.PIPE,
                cwd=repo_dir,
            ).communicate()
            # Create a local ignore file
            fh = open(os.path.join(repo_dir, ".git/info/exclude"), "w")
            fh.write(".git\n.hg\n.svn\n.epio-git\n")
            if os.path.isfile(".epioignore"):
                fh2 = open(".epioignore")
                fh.write(fh2.read())
                fh2.close()
            fh.close()
            # Remove any gitignore files
            for search_dir in os.walk(repo_dir, topdown=False):
                dirpath, dirnames, filenames = search_dir
                if '.gitignore' in filenames:
                    os.remove(os.path.join(dirpath, '.gitignore'))
            # Set configuration options
            fh = open(os.path.join(repo_dir, ".git/config"), "w")
            fh.write("[core]\nautocrlf = false\n")
            fh.close()
            # Add files into git
            subprocess.Popen(
                [git, "add", "."],
                env=env,
                stdout=subprocess.PIPE,
                cwd=repo_dir,
            ).communicate()
            # Commit them all
            subprocess.Popen(
                [git, "commit", "-a", "-m", "Auto-commit."],
                env=env,
                stdout=subprocess.PIPE,
                cwd=repo_dir,
            ).communicate()
            # Push it
            subprocess.Popen(
                [git, "push", "-q", "vcs@%s:%s" % (
                    os.environ.get('EPIO_UPLOAD_HOST', os.environ.get('EPIO_HOST', 'upload.ep.io')).split(":")[0],
                    app,
                ), "master"],
                env=env,
                cwd=repo_dir,
            ).communicate()
        finally:
            # Remove the repo
            shutil.rmtree(temp_dir, ignore_errors=True)
