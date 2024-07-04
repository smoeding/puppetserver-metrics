# Tuning

The description of the script output and tuning hints will be described using the following screenshot. It shows a snapshot of the metrics on a Puppetserver supporting more than 1000 nodes. The system has 6 CPU cores and 20GB of RAM.

The Puppetserver has been configured with a JVM heap size of 8GB. Specifically the following Java arguments are used for this Puppetserver:

```
JAVA_ARGS="-Xmx8g -Xms8g -XX:ReservedCodeCacheSize=768m -XX:ParallelGCThreads=4 \
		   -Djruby.logger.class=com.puppetlabs.jruby_utils.jruby.Slf4jLogger"
```

![Screenshot](Screenshot.png)

## Layout

The first line of the screen shows the name of the Puppetserver on the left side and the time when the metrics were taken on the right side.

The remaining screen contains six areas in a three rows and two columns format. These areas are filled with five graphical panels and a text panel on the top right position.

The top row panels (JVM) present metrics about the Java Virtual Machine running the code of the Puppetserver. The graphical panel on the left side shows the current CPU time usage and heap size of the JVM. The text panel on the right displays the number of JVM threads and some system statistics like load average, number of CPU cores and size of system memory.

The middle row panels (REQ) has metrics about the requests arriving at the system. The left panel contains metrics about the request rate and the right panel shows the rate at which the queue limit is hit.

The bottom row panels (JRUBY) contains metrics about the JRuby utilization. On the left side the number of JRubies in-use is displayed while the right hand side has the service and wait times.

All panels contain on the right hand side a number that indicates the scale of the presented values. The JVM panel on the top left has two scale values since CPU time and memory size are shown. The other panels use a common scale for the displayed values which makes it easier to compare the two values. The displayed range of the panels automatically adjusts to the largest measured value.

## Metrics in detail

### CPU Time

The CPU Time graph shows the normalized amount of CPU Time that the JVM has used in the last interval. It is normalized so that the figure represents the mean number of CPU seconds used per second. The example shows that the Puppetserver has six CPU cores available (see the top right System panel) and has used 5.26 CPU seconds per second in the last interval. That results in a CPU utilization of 87.6 percent. Note that the number here only accounts for the Puppetserver process and does not include other processes like the PuppetDB on the server.

Use the CPU Time output to verify that your machine has enough CPU capacity for the workload. You might notice that this value has a high variation. This is quiet normal on a busy server. On one hand the agents normally connect on almost random times (depending on when the agent was started) and different nodes have different demands due to variations in their catalog.

If the CPU Time used is fairly high over an extended time interval, then you might benefit from more CPU cores on your Puppetserver.

But note that the CPU demand is higher just after the Puppetserver has been started. This is caused by the way the JVM optimizes the running code. When the JVM starts executing, it does not have any detailed information about the resource usage of the program. But while running the program the JVM also collects data about the hotspots in the code. This data is used to decide what code segments are used the most. These code segments are then optimized using more sophisticated techniques. As a result the performance of the application gets better after it has run for some time. Which also means that the resource demand is higher when the application has just been started.

### Heap

The bottom bar in the top left panel shows the current size of the JVM heap. Currently we have 5.64GB of memory allocated with a limit of 8GB. That number will change often on a busy Puppetserver like this.

Normally you will see the following pattern for the heap usage. The usage will swing between a specific lower value and the maximum space available. Just before the heap is filled, the garbage collector will kick in an collect unused object to make space for new objects in the heap. You can use the swing pattern to check the garbage collector timing.

If the sizing of the heap is adequate, you will see an increasing usage from one refresh interval to the next. Ideally this could take 30 seconds or more before the heap is full. Then the allocation will drop to certain value just before the heap seems to be filled completely. In my case the heap does not drop below about 3GB usage. This gives me around 5GB of heap space to use, before the garbage collector needs to run again.

If the heap is to small, you will probably see what looks like random values every time. That is an indication that the garbage collector needs to run very often. Performance will suffer in this case.

Java garbage collection is a well researched and documented area. Use your favorite search engine for more details.

### Request Rate

The panel on the middle left shows the rate of requests arriving at the Puppetserver. The top graph depicts the mean arrival rate (&lambda; in queueing theory designation). The lower graph also shows the mean arrival rate but this time it is only calculated for the last minute. In the example we see a mean arrival rate of 11.8 requests per second while the arrival rate for the last minute is given as 26.9 requests per second.

This difference tells us about the heterogeneity of arrivals for this system. If the rate of the last minute differs significantly from the mean, then there are to be times of high load and other times of low load. This indicates that a certain number of agents seem to connect at the same time. System utilization might be better if the demand could be distributed better over time. Maybe the `splay` parameter in the Puppet configuration could help.

### Queue Limit Hit Rate

The panel on the middle right gives the rate at which the queue limit is hit. In this case the request is rejected (a HTTP/503 *Service Unavailable* response is returned) and the agent might try again later. I believe this metric only has useful values if you have set the `max-queued-requests` configuration parameter for the Puppetserver.

Obviously the system performance could be better if this metric shows non-zero values. Again the upper bar shows the mean rate while the lower bar has the mean rate over the last minute.

### JRuby Usage

A JRuby is an interpreter instance to execute Ruby code inside the Java virtual machine. The number of JRubies is usually configured automatically depending on the number of CPU cores of the Puppetserver. But they can also be defined with the Puppetserver setting `max-active-instances`. Each request to the Puppetserver (upload facts, compile catalog, send file, ...) will need a JRuby instance to execute the relevant Ruby code to fulfill the request. The JRubies are managed as a resource pool so that a JRuby instance is borrowed from the pool to handle a request and then returned to the pool to be available for the next request.

The top graph of the left panel shows the mean number of JRubies that are in-use. The lower graph indicates the number of JRubies that are currently in-use. If the Puppetserver has no free JRubies, it will have to queue the request until a JRuby is returned the pool. So you might want to increase the number of JRuby instances if these metrics indicate, that all JRubies are in use most of the time.

In the example the mean number of allocated JRubies is 4.67 while at the specific point in time all six JRubies were in-use and therefore unavailable to handle the next request.

### JRuby Service and Wait Time

The bottom right panel shows the mean service time for a JRuby in the upper graph. This is the mean time that the JRuby is allocated from the pool and is used to fulfil a request. The lower graph in the panel contains the mean wait time that a request will have before a JRuby is available to handle the request.

Both times are presented in milliseconds. So for the given example we have a mean service time of 145.1ms and a mean wait time of 117.8ms. Waiting time is always a bad sign so in this case performance will suffer significantly.

These measurements match the data from the usage graph as most of the time there doesn't seem to be a free JRuby in the pool to handle a new request when it arrives.
