import rubrik_oracle_module as rbk
import click
import datetime
import pytz
import json


@click.command()
@click.argument('host_cluster_db')
@click.argument('target_host')
@click.option('--time_restore', '-t', type=str, help='Point in time to mount the DB, iso format is YY:MM:DDTHH:MM:SS example 2019-01-01T20:30:15')
def cli(host_cluster_db, target_host, time_restore):
    """Live mount a Rubrik Oracle Backup.

\b
    Gets the backup for the Oracle database on the Oracle database host and will live mount it on the host provided.
\b
    Args:
        host_cluster_db (str): The hostname the database is running on : The database name
        target_host (str): The host to live mount the database. (Must be a compatible Oracle host on Rubrik)
        time_restore: The point in time for the live mount iso 8601 format (2019-04-30T18:23:21)
\b
    Returns:
        live_mount_info (json); JSON text file with the Rubrik cluster response to the live mount request
    """
    rubrik = rbk.connect_rubrik()
    cluster_info = rbk.get_cluster_info(rubrik)
    timezone = cluster_info['timezone']['timezone']
    print("Connected to cluster: {}, version: {}, Timezone: {}.".format(cluster_info['name'], cluster_info['version'], timezone))
    host_cluster_db = host_cluster_db.split(":")
    oracle_db_id = rbk.get_oracle_db_id(rubrik, host_cluster_db[1], host_cluster_db[0])
    oracle_db_info = rbk.get_oracle_db_info(rubrik, oracle_db_id)
    # If source DB is RAC then the target for the live mount must be a RAC cluster
    if 'racName' in oracle_db_info.keys():
        if oracle_db_info['racName']:
            host_id = rbk.get_rac_id(rubrik, cluster_info['id'], target_host)
    else:
        host_id = rbk.get_host_id(rubrik, cluster_info['id'], target_host)
    if time_restore:
        time_ms = rbk.epoch_time(time_restore, timezone)
        print("Using {} for mount.". format(time_restore))
    else:
        print("Using most recent recovery point for mount.")
        oracle_db_info = rbk.get_oracle_db_info(rubrik, oracle_db_id)
        time_ms = rbk.epoch_time(oracle_db_info['latestRecoveryPoint'], timezone)
    print("Starting Live Mount of {} on {}.".format(host_cluster_db[1], target_host))
    live_mount_info = rbk.live_mount(rubrik, oracle_db_id, host_id, time_ms)
    # Set the time format for the printed result
    cluster_timezone = pytz.timezone(timezone)
    utc = pytz.utc
    start_time = utc.localize(datetime.datetime.fromisoformat(live_mount_info['startTime'][:-1])).astimezone(cluster_timezone)
    fmt = '%Y-%m-%d %H:%M:%S %Z'
    print("Live mount status: {}, Started at {}.".format(live_mount_info['status'], start_time.strftime(fmt)))
    return json.dumps(live_mount_info)


if __name__ == "__main__":
    cli()
