#!/usr/bin/python3
#
# Copyright (c) 2023, 2024, 2025, Stefan Möding
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
#

"""
Puppetserver Metrics using terminal based graphics.
"""

import os
import ssl
import sys
import json
import math
import time
import curses
import signal
import socket
import getpass
import argparse
import threading
import configparser
import urllib.request

from os import access, R_OK
from os.path import isfile

##############################################################################
#
class CustomException(Exception):
    """The custome exceptions thrown by the application code."""

##############################################################################
#
class Widget:
    """Show data graphically in a box on screen."""

    @staticmethod
    def unit(value, precision=0):
        """Format a value for output."""

        if value > 2**30:
            return "{value:.{precision}f}G".format(value=value / 2**30, precision=precision)
        if value > 2**20:
            return "{value:.{precision}f}M".format(value=value / 2**20, precision=precision)
        if value > 2**10:
            return "{value:.{precision}f}K".format(value=value / 2**10, precision=precision)

        return "{value:.{precision}f}".format(value=value, precision=precision)

    @staticmethod
    def limitlabel(value):
        """Calculate the limit and label for a value."""

        if value <= 10:
            limit = math.ceil(value)
            label = "{:<3.3}".format("{:.0f}".format(limit))
        elif value <= 100:
            limit = math.ceil(value / 10) * 10
            label = "{:<3.3}".format("{:.0f}".format(limit))
        elif value <= 1000:
            limit = math.ceil(value / 100) * 100
            label = "{:<3.3}".format("{:.0f}".format(limit))
        elif value <= 1024000:
            limit = math.ceil(value / 2**10) * 2**10
            label = "{:<3.3}".format("{:.0f}K".format(limit / 2**10))
        elif value <= 1024000000:
            limit = math.ceil(value / 2**20) * 2**20
            label = "{:<3.3}".format("{:.0f}M".format(limit / 2**20))
        else:
            limit = math.ceil(value / 2**30) * 2**30
            label = "{:<3.3}".format("{:.0f}G".format(limit / 2**30))

        return limit, label

    def __init__(self, screen, y, x):
        self.uoffset = 5
        self.loffset = 5

        self._upper_limit = None
        self._lower_limit = None

        # Paint the graphics we use
        self.window = screen.subwin(6, 34, y, x)

        self.window.addch(0, 2, curses.ACS_ULCORNER)
        self.window.hline(0, 3, curses.ACS_HLINE, 26)
        self.window.addch(0, 28, curses.ACS_HLINE)
        self.window.addch(0, 29, curses.ACS_URCORNER)

        self.window.addch(1, 2, curses.ACS_VLINE)
        self.window.addch(1, 29, curses.ACS_VLINE)

        self.window.addstr(2, 0, "0")
        self.window.addch(2, 2, curses.ACS_LTEE)
        self.window.hline(2, 3, curses.ACS_HLINE, 26)
        self.window.addch(2, 29, curses.ACS_RTEE)

        self.window.addch(3, 2, curses.ACS_VLINE)
        self.window.addch(3, 29, curses.ACS_VLINE)

        self.window.addch(4, 2, curses.ACS_LLCORNER)
        self.window.hline(4, 3, curses.ACS_HLINE, 26)
        self.window.addch(4, 29, curses.ACS_LRCORNER)

    def upper_title(self, title):
        """Set upper title."""

        self.window.addstr(0, 3, " {:<24}".format(title))
        self.uoffset += len(title)

    def lower_title(self, title):
        """Set lower title."""

        self.window.addstr(4, 3, " {:<24}".format(title))
        self.loffset += len(title)

    def upper_limit(self, value):
        """Set and display limit for upper widget part."""

        if (self._upper_limit is None) or (value > self._upper_limit):
            limit, label = Widget.limitlabel(value)

            self._upper_limit = limit

            self.window.addstr(1, 31, label)
            self.window.refresh()

    def lower_limit(self, value):
        """Set and display limit for lower widget part."""

        if (self._lower_limit is None) or (value > self._lower_limit):
            limit, label = Widget.limitlabel(value)

            self._lower_limit = limit

            self.window.addstr(3, 31, label)
            self.window.refresh()

    def limit(self, value):
        """Set and display limit for lower and upper widget part."""

        if ((self._upper_limit is None) or (value > self._upper_limit) or
            (self._lower_limit is None) or (value > self._lower_limit)):
            limit, label = Widget.limitlabel(value)

            self._upper_limit = limit
            self._lower_limit = limit

            self.window.addstr(2, 31, label)
            self.window.refresh()

    def uvalue(self, value, precision=0):
        """Set and display value for the upper widget part."""

        self.upper_limit(value)

        val = "({})".format(Widget.unit(value, precision))
        out = val.ljust(28-self.uoffset)
        self.window.addstr(0, self.uoffset, out)

        pct = (value / self._upper_limit) if (value > 0) else 0.0

        for x in range(0, 26):
            self.window.addch(1, 3+x, curses.ACS_CKBOARD if ((x / 26) < pct) else " ")

        self.window.refresh()

    def lvalue(self, value, precision=0):
        """Set and display value for the lower widget part."""

        self.lower_limit(value)

        val = "({})".format(Widget.unit(value, precision))
        out = val.ljust(28-self.loffset)
        self.window.addstr(4, self.loffset, out)

        pct = (value / self._lower_limit) if (value > 0) else 0.0

        for x in range(0, 26):
            self.window.addch(3, 3+x, curses.ACS_CKBOARD if ((x / 26) < pct) else " ")

        self.window.refresh()

##############################################################################
#
class Metric:
    """Fetch metrics from a Puppetserver using the Metrics API."""

    # These are class variables so that all derived classes with their
    # instances can access the same set of parameters

    context = None
    puppetserver = None
    port = None

    @classmethod
    def initialize(cls, context, puppetserver, port):
        """Initialize class variables."""

        cls.context, cls.puppetserver, cls.port = context, puppetserver, port

    def __init__(self, category, param_name=None, param_type=None):
        param = []

        if param_type is not None:
            param.append(f"type={param_type}")

        if param_name is not None:
            param.append(f"name={param_name}")

        params = ",".join(param)

        url = f"https://{Metric.puppetserver}:{Metric.port}/metrics/v2/read/{category}:{params}"

        self.request = urllib.request.Request(url=url)
        self.request.add_header('User-Agent', 'Puppetserver-Metrics/1.0')

        self.last_timestamp = None
        self.curr_timestamp = None

        self.metrics = {}

    def keys(self):
        """Return all keys of the value dict."""

        value = self.metrics.get('value')

        return value.keys() if value is not None else None

    def value(self, *keys):
        """Return a value from a dict by digging into it using multiple keys."""

        value = self.metrics.get('value')

        for key in keys:
            if value is not None:
                value = value.get(key)

        return value

    def timedelta(self):
        """Return the time difference between current and last metrics."""

        if self.last_timestamp is None or self.curr_timestamp is None:
            return None

        return self.curr_timestamp - self.last_timestamp

    def refresh(self):
        """Fetch updated metrics from the server."""

        with urllib.request.urlopen(self.request, context=Metric.context) as response:
            if response.status == 200:
                data = response.read()

                # Parse JSON and store as object
                self.metrics = json.loads(data)

                if self.metrics:
                    self.last_timestamp = self.curr_timestamp
                    self.curr_timestamp = self.metrics['timestamp']

##############################################################################
#
class OperatingSystemMetrics(Metric):
    """Metrics for the operating system."""

    def __init__(self):
        super().__init__('java.lang', param_type='OperatingSystem')
        self.prev_value = None
        self.refresh()

    def refresh(self):
        """Refresh the metrics."""

        super().refresh()

        self.available_processors = self.value('AvailableProcessors')
        self.physical_memory_size = self.value('TotalPhysicalMemorySize')
        self.system_load_average = self.value('SystemLoadAverage')

    @property
    def process_cpu_time(self):
        """Getter method for the CPU time used by the Puppetserver."""

        value = self.value('ProcessCpuTime')
        delta = None

        if value is not None:
            # convert to seconds
            value /= 1000000000

            delta = 0 if (self.prev_value is None) else (value - self.prev_value) / self.timedelta()
            self.prev_value = value

        return delta

##############################################################################
#
class MemoryMetrics(Metric):
    """Metrics for the memory used in the Java VM."""

    # pylint: disable=line-too-long

    def __init__(self):
        super().__init__('puppetserver', param_name='puppetlabs.localhost.memory.*')
        self.refresh()

    def refresh(self):
        """Refresh the metrics."""

        super().refresh()

        self.heap_memory_max = self.value('puppetserver:name=puppetlabs.localhost.memory.heap.max', 'Value')
        self.heap_memory_used = self.value('puppetserver:name=puppetlabs.localhost.memory.heap.used', 'Value')

##############################################################################
#
class ThreadingMetrics(Metric):
    """Metrics for the threads used in the Java VM."""

    def __init__(self):
        super().__init__('java.lang', param_type='Threading')
        self.refresh()

    def refresh(self):
        """Refresh the metrics."""

        super().refresh()

        self.thread_count = self.value("ThreadCount")
        self.peak_thread_count = self.value("PeakThreadCount")
        self.daemon_thread_count = self.value("DaemonThreadCount")

##############################################################################
#
class JRubyMetrics(Metric):
    """Metrics for the JRuby instances used in the Java VM."""

    # pylint: disable=too-many-instance-attributes, line-too-long

    def __init__(self):
        super().__init__('puppetserver', param_name='puppetlabs.localhost.jruby.*')
        self.refresh()

    def refresh(self):
        """Refresh the metrics."""

        super().refresh()

        self.num_rubies = self.value('puppetserver:name=puppetlabs.localhost.jruby.num-jrubies', 'Value')
        self.used_rubies = self.num_rubies - self.value('puppetserver:name=puppetlabs.localhost.jruby.num-free-jrubies', 'Value')
        self.mean_used_rubies = self.num_rubies - self.value('puppetserver:name=puppetlabs.localhost.jruby.free-jrubies-histo', 'Mean')

        self.request_rate_mean = self.value('puppetserver:name=puppetlabs.localhost.jruby.borrow-timer', 'MeanRate')
        self.request_rate_1min = self.value('puppetserver:name=puppetlabs.localhost.jruby.borrow-timer', 'OneMinuteRate')

        self.queue_limit_rate_mean = self.value('puppetserver:name=puppetlabs.localhost.jruby.queue-limit-hit-meter', 'MeanRate')
        self.queue_limit_rate_1min = self.value('puppetserver:name=puppetlabs.localhost.jruby.queue-limit-hit-meter', 'OneMinuteRate')

        self.borrow_time_mean = self.value('puppetserver:name=puppetlabs.localhost.jruby.borrow-timer', 'Mean')
        self.wait_time_mean = self.value('puppetserver:name=puppetlabs.localhost.jruby.wait-timer', 'Mean')

##############################################################################
#
class Application():
    """The metrics collector application."""

    # pylint: disable=too-many-instance-attributes, line-too-long

    screen = None
    widget1 = None
    widget2 = None
    widget3 = None
    widget4 = None
    widget5 = None
    metric1 = None
    metric2 = None
    metric3 = None
    metric4 = None

    def __init__(self, puppetserver, port=8140, interval=3, verbose=False):
        self.puppetserver = puppetserver
        self.port = port
        self.refresh_interval = interval
        self.verbose = verbose
        self.done = threading.Event()

        # Catch the signals usually used to terminate the program. We do this
        # to be able to clean up the screen by calling curses.endwin() in the
        # finally block below.

        signal.signal(signal.SIGHUP, self.setdone)
        signal.signal(signal.SIGINT, self.setdone)
        signal.signal(signal.SIGTERM, self.setdone)

    def setdone(self, _signo, _frame):
        """This method will be called if a signal is received. In this case
        we take a note of the event. The main loop will terminate as
        a result.
        """
        self.done.set()

    def tryfile(self, file, description):
        """Check if a file exists and is readable."""

        if isfile(file):
            if self.verbose:
                print(f"{description} {file} exists")

            if access(file, R_OK):
                if self.verbose:
                    print(f"{description} {file} is readable")
                return True

        if self.verbose:
            print(f"{description} {file} is not readable or does not exist")

        return False

    def setup(self):
        """Setup the application."""

        fqdn = socket.getfqdn()
        user = getpass.getuser()
        home = os.path.expanduser('~')

        if user is None:
            raise CustomException("Can't determine your username")

        #
        # Read settings from puppet.conf
        #
        config = configparser.ConfigParser(strict=True)
        config.read_dict({'agent': {'server': 'puppet'}})

        puppetconf = os.path.join(home, '.puppetlabs/etc/puppet/puppet.conf')

        if self.tryfile(puppetconf, 'Puppet settings'):
            config.read(puppetconf)
        else:
            puppetconf = '/etc/puppetlabs/puppet/puppet.conf'
            if self.tryfile(puppetconf, 'Puppet settings'):
                config.read(puppetconf)

        # Use name of Puppetserver from the config file or the script options
        if self.puppetserver is None:
            self.puppetserver = config['agent']['server']

        if self.verbose:
            print(f"Using puppetserver {self.puppetserver}")

        #
        # Certificate files used by the standard Puppet installation
        #
        cacert = os.path.join(home, '.puppetlabs/etc/puppet/ssl/certs/ca.pem')

        if not self.tryfile(cacert, 'CA certificate'):
            cacert = '/etc/puppetlabs/puppet/ssl/certs/ca.pem'

            if not self.tryfile(cacert, 'CA certificate'):
                raise CustomException('No usable CA certificate found')

        # Certificate
        cert = os.path.join(home, f".puppetlabs/etc/puppet/ssl/certs/{user}.pem")

        if not self.tryfile(cert, 'Client certificate'):
            cert = f"/etc/puppetlabs/puppet/ssl/certs/{fqdn}.pem"

            if not self.tryfile(cert, 'Client certificate'):
                raise CustomException('No usable client certificate found')

        # Key
        key = os.path.join(home, f".puppetlabs/etc/puppet/ssl/private_keys/{user}.pem")

        if not self.tryfile(key, 'Client key'):
            key = f"/etc/puppetlabs/puppet/ssl/private_keys/{fqdn}.pem"

            if not self.tryfile(key, 'Client key'):
                raise CustomException('No usable client key found')

        # Create SSL context for client authentication
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=cacert)
        ctx.load_cert_chain(cert, key)

        # TLSv1.3 would be nice but might not (yet) be available everywhere
        #ctx.minimum_version = ssl.TLSVersion.TLSv1_3

        # All metrics are fetched from the same Puppetserver
        Metric.initialize(ctx, self.puppetserver, self.port)

    def initscreen(self):
        """Initialize the screen and generate the GUI."""

        self.screen = curses.initscr()
        self.screen.addstr(0, 0, f'Node: {self.puppetserver}')
        self.screen.addstr(0, 30, 'Puppetserver Metrics')
        self.screen.addstr(0, 50, time.asctime().rjust(30))

        # Threads panel
        self.screen.addstr(3, 48, "{:^13}".format("JVM Threads"))
        self.screen.addstr(4, 48, "{:<8}".format("Current:"))
        self.screen.addstr(5, 48, "{:<8}".format("Daemon:"))
        self.screen.addstr(6, 48, "{:<8}".format("Peak:"))

        # System panel
        self.screen.addstr(3, 63, "{:^10}".format("System"))
        self.screen.addstr(4, 63, "{:<7}".format("Load:"))
        self.screen.addstr(5, 63, "{:<7}".format("CPUs:"))
        self.screen.addstr(6, 63, "{:<7}".format("Mem:"))

        # JVM panel
        self.screen.addstr(5, 0, 'JVM')
        self.widget1 = Widget(self.screen, 3, 8)
        self.widget1.upper_title('CPU Time')
        self.widget1.lower_title('Heap')
        self.widget1.upper_limit(self.metric1.available_processors)
        self.widget1.lower_limit(self.metric2.heap_memory_max)

        # Request panel
        self.screen.addstr(12, 0, 'REQ')
        self.widget2 = Widget(self.screen, 10, 8)
        self.widget2.upper_title('Mean Rate')
        self.widget2.lower_title('1min Rate')

        # Queue Limit panel
        self.widget3 = Widget(self.screen, 10, 45)
        self.widget3.upper_title('Mean Q-Lim Rate')
        self.widget3.lower_title('1min Q-Lim Rate')

        # JRUBY panels
        self.screen.addstr(19, 0, 'JRUBY')
        self.widget4 = Widget(self.screen, 17, 8)
        self.widget4.upper_title('Mean In-Use')
        self.widget4.lower_title('Current In-Use')
        self.widget4.limit(self.metric4.num_rubies)

        self.widget5 = Widget(self.screen, 17, 45)
        self.widget5.upper_title('Service Time')
        self.widget5.lower_title('Wait Time')

    def run(self):
        """The main loop of the application code."""

        self.metric1 = OperatingSystemMetrics()
        self.metric2 = MemoryMetrics()
        self.metric3 = ThreadingMetrics()
        self.metric4 = JRubyMetrics()

        #
        # GUI
        #
        try:
            self.initscreen()

            # Display initial screen
            self.screen.refresh()

            while not self.done.is_set():
                loop_time = time.time()
                next_loop_time = loop_time + self.refresh_interval

                # Refresh all metrics
                self.metric1.refresh()
                self.metric2.refresh()
                self.metric3.refresh()
                self.metric4.refresh()

                # JVM Threads
                self.screen.addstr(4, 56, "{:5d}".format(self.metric3.thread_count))
                self.screen.addstr(5, 56, "{:5d}".format(self.metric3.daemon_thread_count))
                self.screen.addstr(6, 56, "{:5d}".format(self.metric3.peak_thread_count))

                # Node
                self.screen.addstr(4, 69, "{:5.2f}".format(self.metric1.system_load_average))
                self.screen.addstr(5, 69, "{:5d}".format(self.metric1.available_processors))
                self.screen.addstr(6, 69, "{:>5}".format(Widget.unit(self.metric1.physical_memory_size)))

                # JVM
                self.widget1.uvalue(self.metric1.process_cpu_time, 2)
                self.widget1.lvalue(self.metric2.heap_memory_used, 2)

                # HTTP request rate
                self.widget2.limit(self.metric4.request_rate_mean)
                self.widget2.limit(self.metric4.request_rate_1min)

                self.widget2.uvalue(self.metric4.request_rate_mean, 1)
                self.widget2.lvalue(self.metric4.request_rate_1min, 1)

                # Queue Limit Hit Rate
                self.widget3.limit(self.metric4.queue_limit_rate_mean)
                self.widget3.limit(self.metric4.queue_limit_rate_1min)

                self.widget3.uvalue(self.metric4.queue_limit_rate_mean, 2)
                self.widget3.lvalue(self.metric4.queue_limit_rate_1min, 2)

                # JRubies in-use
                self.widget4.uvalue(self.metric4.mean_used_rubies, 2)
                self.widget4.lvalue(self.metric4.used_rubies)

                # JRubies service and wait time
                self.widget5.limit(self.metric4.borrow_time_mean)
                self.widget5.limit(self.metric4.wait_time_mean)

                self.widget5.uvalue(self.metric4.borrow_time_mean, 1)
                self.widget5.lvalue(self.metric4.wait_time_mean, 1)

                # Print current timestamp
                self.screen.addstr(0, 50, time.asctime(time.localtime(loop_time)).rjust(30))

                self.screen.refresh()

                # Calculate delay based on the start time of the loop
                self.done.wait(next_loop_time - time.time())

        finally:
            curses.endwin()

#
# Let's roll
#
if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("-v", "--verbose",
                            help="be more verbose",
                            action="store_true")
        parser.add_argument("--interval",
                            help="the interval between updates in seconds",
                            type=int,
                            default=3)
        parser.add_argument("--server",
                            help="the Puppetserver to use (default 'puppet')")
        parser.add_argument("--key",
                            help="the SSL private key used for authentication")
        parser.add_argument("--cert",
                            help="the SSL client certificate")
        parser.add_argument("--cacert",
                            help="the SSL certificate file to verify the peer")
        parser.add_argument("--no-proxy",
                            help="ignore proxy environment variables",
                            action="store_true")

        args = parser.parse_args()

        # Disable proxy settings inherited from the shell environment
        if args.no_proxy:
            for var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
                if var in os.environ:
                    del os.environ[var]
                    if args.verbose:
                        print(f"Removed environment variable {var}")

        app = Application(args.server, 8140, args.interval, args.verbose)
        app.setup()
        app.run()
    except Exception as excp:
        sys.exit(f"{sys.argv[0]}: {excp}")
