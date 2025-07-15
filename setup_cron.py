#!/usr/bin/env python3
"""
Script to set up a cron job for the Email Classifier.
"""
import os
import sys
import subprocess
import argparse
from crontab import CronTab
from pathlib import Path


def setup_cron_job(schedule='0 2 * * *', user=None):
    """
    Set up a cron job to run the Email Classifier.
    
    Args:
        schedule: Cron schedule expression (default: run at 2 AM daily).
        user: User to set up the cron job for (default: current user).
    
    Returns:
        bool: True if the cron job was set up successfully, False otherwise.
    """
    try:
        # Get the absolute path to the project directory
        project_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Get the absolute path to the Python executable
        python_executable = sys.executable
        
        # Create the command to run
        command = f"cd {project_dir} && {python_executable} {project_dir}/main.py"
        
        # Set up the cron job
        cron = CronTab(user=user)
        job = cron.new(command=command)
        job.setall(schedule)
        job.set_comment('Email Classifier')
        
        # Write the cron job to the crontab
        cron.write()
        
        print(f"Cron job set up successfully with schedule: {schedule}")
        print(f"Command: {command}")
        return True
    except Exception as e:
        print(f"Error setting up cron job: {e}")
        return False


def remove_cron_job(user=None):
    """
    Remove the Email Classifier cron job.
    
    Args:
        user: User to remove the cron job for (default: current user).
    
    Returns:
        bool: True if the cron job was removed successfully, False otherwise.
    """
    try:
        cron = CronTab(user=user)
        
        # Find and remove jobs with the 'Email Classifier' comment
        count = 0
        for job in cron.find_comment('Email Classifier'):
            cron.remove(job)
            count += 1
        
        # Write the changes to the crontab
        cron.write()
        
        if count > 0:
            print(f"Removed {count} Email Classifier cron job(s)")
            return True
        else:
            print("No Email Classifier cron jobs found")
            return False
    except Exception as e:
        print(f"Error removing cron job: {e}")
        return False


def list_cron_jobs(user=None):
    """
    List all Email Classifier cron jobs.
    
    Args:
        user: User to list cron jobs for (default: current user).
    """
    try:
        cron = CronTab(user=user)
        
        # Find jobs with the 'Email Classifier' comment
        jobs = list(cron.find_comment('Email Classifier'))
        
        if jobs:
            print(f"Found {len(jobs)} Email Classifier cron job(s):")
            for i, job in enumerate(jobs, 1):
                print(f"{i}. Schedule: {job.slices} - Command: {job.command}")
        else:
            print("No Email Classifier cron jobs found")
    except Exception as e:
        print(f"Error listing cron jobs: {e}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Set up a cron job for the Email Classifier')
    parser.add_argument('--schedule', default='0 2 * * *', help='Cron schedule expression (default: run at 2 AM daily)')
    parser.add_argument('--user', help='User to set up the cron job for (default: current user)')
    parser.add_argument('--remove', action='store_true', help='Remove existing Email Classifier cron jobs')
    parser.add_argument('--list', action='store_true', help='List existing Email Classifier cron jobs')
    
    args = parser.parse_args()
    
    # Check if python-crontab is installed
    try:
        import crontab
    except ImportError:
        print("The 'python-crontab' package is required. Installing...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'python-crontab'])
            print("Successfully installed 'python-crontab'")
        except Exception as e:
            print(f"Failed to install 'python-crontab': {e}")
            print("Please install it manually: pip install python-crontab")
            return 1
    
    if args.list:
        list_cron_jobs(user=args.user)
    elif args.remove:
        remove_cron_job(user=args.user)
    else:
        setup_cron_job(schedule=args.schedule, user=args.user)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
