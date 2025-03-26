from ctypes import *
import time
import gpiozero

#include <limits.h>
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h

PTHREAD_STACK_MIN = 131072

SCHED_FIFO = 1

TIMER_ABSTIME = 1
CLOCK_REALTIME = 0
CLOCK_MONOTONIC_RAW	= 4

NSEC_PER_SEC = 1000000000

interval = 200000000

#lc = CDLL('libc.so.6', mode=RTLD_GLOBAL)
lc = CDLL('libc.so.6')

class pthread_attr_t(Union):
    _fields_ = [('__size', c_char*64),
                ('__aling', c_int)]

class sched_param(Structure):    
    _fields_ = [('sched_priority', c_int)]

class timeval(Structure):
    _fields_ = [('t_sec', c_long),
                ('t_nsec', c_long)]

attr = pthread_attr_t()
param = sched_param()
thread = c_void_p()
t_read = timeval()

led1=gpiozero.LED("GPIO4")
def tsnorm(ts):
    while(ts.t_nsec >= NSEC_PER_SEC):
        ts.t_nsec = ts.t_nsec-NSEC_PER_SEC
        ts.t_sec = ts.t_sec+1
    return ts

def thread_func(data):
    t = timeval()
    ts0 = t.t_sec
    lc.clock_gettime(CLOCK_REALTIME, byref(t))
    for ii in range(100):
        led1.off()
        res = lc.clock_nanosleep(CLOCK_REALTIME, TIMER_ABSTIME, byref(t), None)
        led1.on()
        lc.clock_gettime(CLOCK_REALTIME, byref(t_read))
        t.t_nsec = t.t_nsec + interval
        t = tsnorm(t)
        tmp = (t_read.t_sec-t.t_sec)*1e9 + t_read.t_nsec-t.t_nsec+500000000
        print('Latency: ', tmp)
        #param = sched_param()
        time.sleep(0.05)
        #print("Here\n")


def main():
        #  Lock memory */
        #/*if(mlockall(MCL_CURRENT|MCL_FUTURE) == -1) {
        #        printf("mlockall failed: %m\n");
        #        exit(-2);
        #}*/
 
        #/* Initialize pthread attributes (default values) */
        ret = lc.pthread_attr_init(byref(attr))
        if ret !=0:
            print("init pthread attributes failed\n")
            return ret
 
        #/* Set a specific stack size  */
        ret = lc.pthread_attr_setstacksize(byref(attr), PTHREAD_STACK_MIN)
        if ret !=0:
            print("pthread setstacksize failed\n")
            return ret

        #/* Set scheduler policy and priority of pthread */
        ret = lc.pthread_attr_setschedpolicy(byref(attr), SCHED_FIFO);
        if ret !=0:
            print("pthread setschedpolicy failed\n")
            return ret

        param.sched_priority = 90
        ret = lc.pthread_attr_setschedparam(byref(attr), byref(param))
        if ret !=0:
            print("pthread setschedparam failed\n")
            return ret

        ret = lc.pthread_attr_getschedparam(byref(attr), byref(param))
        print("Param %d", param.sched_priority)
        if ret !=0:
            print("pthread getschedparam failed\n")
            return ret

        #/* Use scheduling parameters of attr */
        ret = lc.pthread_attr_setinheritsched(byref(attr), 1) #PTHREAD_EXPLICIT_SCHED);
        if ret !=0:
            print("pthread setinheritsched failed\n")
            return ret
 
        #/* Create a pthread with specified attributes */
        thread_func_ptr = CFUNCTYPE(None, c_void_p)(thread_func)
        ret = lc.pthread_create(byref(thread), byref(attr), thread_func_ptr, None)
        if ret !=0:
            print("create pthread failed\n")
            return ret
 
        #/* Join the thread and wait until it is done */
        ret = lc.pthread_join(thread, None)
        if ret !=0:
            print("join pthread failed: %m\n")
 
        return ret

print(main())
