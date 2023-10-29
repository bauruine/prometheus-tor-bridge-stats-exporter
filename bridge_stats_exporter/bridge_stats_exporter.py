#!/usr/bin/env python

import sys
import argparse
import re
import os
from prometheus_client import generate_latest
from prometheus_client import make_wsgi_app
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, Enum, REGISTRY
from wsgiref.simple_server import make_server


class OnionooCollector(object):
    def __init__(self):
        self.label_list = ['countries', 'ip-versions', 'transports']

    def collect(self):
        # Metrics

        tor_bridge_stats_countries  = GaugeMetricFamily(
            'tor_bridge_stats_countries',
            'Number of connected users per country',
            labels = ['country', 'tor_instance']
        )
        tor_bridge_stats_ip_version = GaugeMetricFamily(
            'tor_bridge_stats_ip_version',
            'Number of connvetions per ip version',
            labels = ['ip_version', 'tor_instance']
        )
        tor_bridge_stats_transport = GaugeMetricFamily(
            'tor_bridge_stats_transports',
            'Number of connections per transport method',
            labels = ['transport', 'tor_instance']
        )
        tor_instances = []
        if os.path.isdir("/var/lib/tor-instances"):
            for instance in os.listdir("/var/lib/tor-instances/"):
                if os.path.isfile(f"/var/lib/tor-instances/{instance}/stats/bridge-stats"):
                    tor_instances.append(f"tor-instances/{instance}")
        if os.path.isfile("/var/lib/tor/stats/bridge-stats"):
            tor_instances.append("tor")

        for instance in tor_instances:
            with open(f"/var/lib/{instance}/stats/bridge-stats") as bridge_file:
                if instance == "tor":
                    tor_instance = "default"
                else:
                    tor_instance = instance.split("/")[1]
                for line in bridge_file.readlines():
                    if not re.search(r'bridge-ip-transports', line):
                        search = re.findall('(\w{2})=(\d+)', line)
                        if search:
                            for entry in search:
                                if re.search(r'bridge-ips', line):
                                    labels = dict(country=entry[0], tor_instance=tor_instance)
                                    tor_bridge_stats_countries.add_metric(list(labels.values()), entry[1])
                                if re.search(r'bridge-ip-versions', line):
                                    labels = dict(ip_version=entry[0], tor_instance=tor_instance)
                                    tor_bridge_stats_ip_version.add_metric(list(labels.values()), entry[1])
                    elif re.search(r'bridge-ip-transports', line):
                        search = re.findall('(\w+)=(\d+)', line)
                        if search:
                            for entry in search:
                                labels = dict(transport=entry[0], tor_instance=tor_instance)
                                tor_bridge_stats_transport.add_metric(list(labels.values()), entry[1])


        yield tor_bridge_stats_countries
        yield tor_bridge_stats_ip_version
        yield tor_bridge_stats_transport


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Onionoo Prometheus exporter.'
    )
    parser.add_argument(
        '--address', metavar='IP', type=str, default='',
        help='Listening address, default: all'
    )
    parser.add_argument(
        '--port', metavar='PORT', type=int, default=9888,
        help='Listening port, default: 9888'
    )
    parser.add_argument(
        '--dump-data', action='store_true', default=False,
        help='Prints collected data and exits'
    )
    args = parser.parse_args()

    REGISTRY.register(OnionooCollector())

    # Test mode
    if args.dump_data:
        print(generate_latest(REGISTRY).decode('utf8'))
        sys.exit(0)

    # Start http server
    app = make_wsgi_app()
    httpd = make_server(args.address, args.port, app)
    httpd.serve_forever()

