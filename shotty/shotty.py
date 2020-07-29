import boto3
import click
import botocore

session = boto3.Session(profile_name='shotty')
ec2 = session.resource('ec2')


def filter_instances(project, instanceId):
    instances = []

    if project:
        filters = [{'Name': 'tag:Project', 'Values': [project]}]
        instances = ec2.instances.filter(Filters=filters)
    else:
        instances = ec2.instances.all()

    if instanceId:
        instances = [i for i in instances if i.id == instanceId]

    return instances


def has_pending_snapshot(volume):
    snapshots = list(volume.snapshots.all())
    return snapshots and snapshots[0] == 'pending'


@click.group()
@click.option('--profile', default="shotty",
              help="specify an AWS cli profile")
def cli(profile):
    """Shotty manages snapshots"""
    print("cli(profile) = {0}".format(profile))
    session = boto3.Session(profile_name=profile)
    ec2 = session.resource('ec2')
    return


@cli.group('snapshots')
def snapshots():
    """Commands for snapshots"""


@snapshots.command('list')
@click.option('--project', default=None,
              help="Only snapshots for project (tag Project:<name>)")
@click.option('--all', 'list_all', default=False, is_flag=True,
              help="List all snapshots")
@click.option('--instance', 'instanceId', default=None, type=str,
              help="Target a specific EC2 instance by Id")
def list_snapshots(project, list_all, instanceId):
    "List EC2 snapshots"
    instances = filter_instances(project, instanceId)
    for i in instances:
        for v in i.volumes.all():
            for s in v.snapshots.all():
                print(', '.join((
                    s.id,
                    v.id,
                    i.id,
                    s.state,
                    s.progress,
                    s.start_time.strftime("%c")
                )))

                if s.state == 'completed' and not list_all:
                    break
    return


@cli.group('volumes')
def volumes():
    """Commands for volumes"""


@volumes.command('list')
@click.option('--project', default=None,
              help="Only volumes for project (tag Project:<name>)")
@click.option('--instance', default=None, type=str,
              help="Only volumes for project (tag Project:<name>)")
@click.option('--instance', 'instanceId', default=None, type=str,
              help="Target a specific EC2 instance by Id")
def list_volumes(project, instanceId):
    "List EC2 volumes"
    instances = filter_instances(project, instanceId)

    for i in instances:
        for v in i.volumes.all():
            print(", ".join((
                v.id,
                i.id,
                v.state,
                str(v.size) + "GiB",
                v.encrypted and "Encrypted" or "Not Encrpted")))

    return


@cli.group('instances')
def instances():
    """Commands for instances"""


@instances.command('list')
@click.option('--project', default=None,
              help="Only instance for project (tag Project:<name>)")
@click.option('--instance', 'instanceId', default=None, type=str,
              help="Target a specific EC2 instance by Id")
def list_instances(project, instanceId):
    "List EC2 instances"
    instances = filter_instances(project, instanceId)

    for i in instances:
        tags = {t['Key']: t['Value'] for t in i.tags or []}
        print(', '.join((
            i.id,
            i.instance_type,
            i.placement['AvailabilityZone'],
            i.state['Name'],
            tags.get('Project', '<no project>'),
            i.public_dns_name)))

    return


@instances.command('stop')
@click.option('--project', default=None,
              help="Stop instances for project (tag Project:<name>)")
@click.option('--force', 'force', default=False, is_flag=True,
              help="If --project is not set, exit command immediately unless --force is set")
@click.option('--instance', 'instanceId', default=None, type=str,
              help="Target a specific EC2 instance by Id")
def stop_instances(project, force, instanceId):
    "Stop EC2 instances"
    if not project and not force:
        print("-project must be set unless --force=True")
        return

    instances = filter_instances(project, instanceId)

    for i in instances:
        print("Stopping {0}...".format(i.id))
        try:
            i.stop()
        except botocore.exceptions.ClientError as e:
            print("Could not stop {0} ".format(i.id) + str(e))
            continue

    return


@instances.command('start')
@click.option('--project', default=None,
              help="Start instances for project (tag Project:<name>)")
@click.option('--force', 'force', default=False, is_flag=True,
              help="If --project is not set, exit command immediately unless --force is set")
@click.option('--instance', 'instanceId', default=None, type=str,
              help="Target a specific EC2 instance by Id")
def start_instances(project, force, instanceId):
    "Start EC2 instances"
    if not project and not force:
        print("-project must be set unless --force=True")
        return

    instances = filter_instances(project, instanceId)

    for i in instances:
        print("Starting {0}...".format(i.id))
        try:
            i.start()
        except botocore.exceptions.ClientError as e:
            print("Could not start {0} ".format(i.id) + str(e))
            continue

    return


@ instances.command('snapshot')
@ click.option('--project', default=None,
               help="Only instances for project (tag Project:<name>)")
@ click.option('--force', 'force', default=False, is_flag=True,
               help="If --project is not set, exit command immediately unless --force is set")
@click.option('--instance', 'instanceId', default=None, type=str,
              help="Target a specific EC2 instance by Id")
def create_snapshots(project, force, instanceId):
    "Create snapshot of volumes attached to EC2 instances"
    if not project and not force:
        print("-project must be set unless --force=True")
        return

    instances = filter_instances(project, instanceId)

    for i in instances:
        try:
            restart = True
            if i.state == 'stopped':
                restart = False
            print("Stopping {0}".format(i.id))
            i.stop()
            i.wait_until_stopped()
            for v in i.volumes.all():
                if has_pending_snapshot(v):
                    print(
                        " Skipping {0}, snapshot already in progress".format(v.id))
                    continue
                print("Creating snapshot of {0}".format(v.id))
                v.create_snapshot(Description="Created by Shotty")

            print("Starting {0}".format(i.id))
            if restart:
                i.start()
                i.wait_until_running()
        except botocore.exceptions.ClientError as e:
            print("Error creating snapshot {0} ".format(i.id) + str(e))
            continue

    print("Job Done")

    return


@ instances.command('reboot')
@ click.option('--project', default=None,
               help="Only instances for project (tag Project:<name>)")
@ click.option('--force', 'force', default=False, is_flag=True,
               help="If --project is not set, exit command immediately unless --force is set")
@click.option('--instance', 'instanceId', default=None, type=str,
              help="Target a specific EC2 instance by Id")
def reboot_instances(project, force, instanceId):
    "Reboot EC2 instances"
    if not project and not force:
        print("-project must be set unless --force=True")
        return

    instances = filter_instances(project, instanceId)

    for i in instances:
        print("Rebooting {0}".format(i.id))
        print("Stopping {0}".format(i.id))
        i.stop()
        i.wait_until_stopped()
        print("Restarting {0}".format(i.id))
        i.start()
        i.wait_until_running()
        print("Reboot for {0} complete".format(i.id))

    print("Rebooting complete")


if __name__ == '__main__':
    cli()
