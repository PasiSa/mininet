"""ELEC-E7320 Internet Protocols course test topologies

Modified from mininet custom topology example.

Usage:
sudo mn -x --custom aalto/topologies.py --link=tc --topo <name>

Where name is 'latency', 'slow', 'buffers', or 'lossy'
"""


from mininet.topo import Topo

class TopoLatency( Topo ):
    "Long latency"

    def __init__( self ):
        "Create custom topo."

        # Initialize topology
        Topo.__init__( self )

        # Add hosts and switches
        leftHost1 = self.addHost( 'lh1' )
        leftHost2 = self.addHost( 'lh2' )
        rightHost1 = self.addHost( 'rh1' )
        rightHost2 = self.addHost( 'rh2' )
        leftSwitch = self.addSwitch( 's1' )
        rightSwitch = self.addSwitch( 's2' )

        # Add links
        self.addLink( leftHost1, leftSwitch )
        self.addLink( leftHost2, leftSwitch )
        self.addLink( leftSwitch, rightSwitch, bw=10, delay='400ms' )
        self.addLink( rightSwitch, rightHost1 )
        self.addLink( rightSwitch, rightHost2 )


class TopoSlow( Topo ):
    "Basic Slow topology small buffers."

    def __init__( self ):
        "Create custom topo."

        # Initialize topology
        Topo.__init__( self )

        # Add hosts and switches
        leftHost1 = self.addHost( 'lh1' )
        leftHost2 = self.addHost( 'lh2' )
        rightHost1 = self.addHost( 'rh1' )
        rightHost2 = self.addHost( 'rh2' )
        leftSwitch = self.addSwitch( 's1' )
        rightSwitch = self.addSwitch( 's2' )

        # Add links
        self.addLink( leftHost1, leftSwitch )
        self.addLink( leftHost2, leftSwitch )
        self.addLink( leftSwitch, rightSwitch, max_queue_size=5, bw=0.1, delay='200ms' )
        self.addLink( rightSwitch, rightHost1 )
        self.addLink( rightSwitch, rightHost2 )


class TopoSlowBuffered( Topo ):
    "Slow overbuffered bottleneck."

    def __init__( self ):
        "Create custom topo."

        # Initialize topology
        Topo.__init__( self )

        # Add hosts and switches
        leftHost1 = self.addHost( 'lh1' )
        leftHost2 = self.addHost( 'lh2' )
        rightHost1 = self.addHost( 'rh1' )
        rightHost2 = self.addHost( 'rh2' )
        leftSwitch = self.addSwitch( 's1' )
        rightSwitch = self.addSwitch( 's2' )

        # Add links
        self.addLink( leftHost1, leftSwitch )
        self.addLink( leftHost2, leftSwitch )
        self.addLink( leftSwitch, rightSwitch, max_queue_size=200, bw=0.1, delay='200ms' )
        self.addLink( rightSwitch, rightHost1 )
        self.addLink( rightSwitch, rightHost2 )


class TopoLossy( Topo ):
    "10% packet loss rate"

    def __init__( self ):
        "Create custom topo."

        # Initialize topology
        Topo.__init__( self )

        # Add hosts and switches
        leftHost1 = self.addHost( 'lh1' )
        leftHost2 = self.addHost( 'lh2' )
        rightHost1 = self.addHost( 'rh1' )
        rightHost2 = self.addHost( 'rh2' )
        leftSwitch = self.addSwitch( 's1' )
        rightSwitch = self.addSwitch( 's2' )

        # Add links
        self.addLink( leftHost1, leftSwitch )
        self.addLink( leftHost2, leftSwitch )
        self.addLink( leftSwitch, rightSwitch, loss=10, bw=10, delay='20ms' )
        self.addLink( rightSwitch, rightHost1 )
        self.addLink( rightSwitch, rightHost2 )


topos = { 'latency': ( lambda: TopoLatency() ),
          'slow': (lambda: TopoSlow() ),
          'buffers': ( lambda: TopoSlowBuffered() ),
          'lossy': (lambda: TopoLossy() )
}
