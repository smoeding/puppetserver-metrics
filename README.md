# Puppet Server Metrics

This Python3 script uses the [Puppet Server V2 metrics API](https://www.puppet.com/docs/puppet/8/server/metrics-api/v2/metrics_api.html) to repeatedly show performance metrics of your Puppetserver. The curses library is used to present the metrics using ASCII graphics in a terminal window.

This script might be useful for consultants visiting a Customer to investigate suspected performance problems with the Puppetserver. It only needs a default Python interpreter and provides graphical monitoring without any additional software installation. But it can of course be used by every other puppeteer as well. See the following screenshot for an example output.

![Screenshot](Screenshot.png)

You can use the `--help` argument to display the usage message:

```
usage: puppetserver-metrics.py [-h] [-v] [--interval INTERVAL]
                               [--server SERVER] [--key KEY] [--cert CERT]
                               [--cacert CACERT] [--no-proxy]

optional arguments:
  -h, --help           show this help message and exit
  -v, --verbose        be more verbose
  --interval INTERVAL  the interval between updates in seconds
  --server SERVER      the Puppetserver to use (default 'puppet')
  --key KEY            the SSL private key used for authentication
  --cert CERT          the SSL client certificate
  --cacert CACERT      the SSL certificate file to verify the peer
  --no-proxy           ignore proxy environment variables
```

Normally the screen is updated every three seconds. You can set a different refresh rate using the `--interval` parameter.

*Fun Fact*: If the appearance of the graphics looks familiar to you, then you are probably old enough to have worked with the VAX/VMS respectively OpenVMS operating system: the layout of the metric panels has been inspired by the VMS `MONITOR SYSTEM` utility.

## Installation and configuration

See the separate [INSTALL](INSTALL.md) document.

## Tuning

Details about the output and some tuning hints are given in the additional [TUNING](TUNING.md) reference.
