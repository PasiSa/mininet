"""Custom topology example

Two directly connected switches plus a host for each switch:

   host --- switch --- switch --- host

Adding the 'topos' dict with a key/value pair to generate our newly defined
topology enables one to pass in '--topo=mytopo' from the command line.
"""

from mininet.topo import Topo

class TopoLatency( Topo ):
    "Basic Latency topology for ELEC-E7320."

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
        self.addLink( leftSwitch, rightSwitch, bw=10, delay='200ms' )
        self.addLink( rightSwitch, rightHost1 )
        self.addLink( rightSwitch, rightHost2 )

class TopoSlow( Topo ):
    "Basic Slow topology for ELEC-E7320."

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
        self.addLink( leftSwitch, rightSwitch, bw=0.05, delay='200ms' )
        self.addLink( rightSwitch, rightHost1 )
        self.addLink( rightSwitch, rightHost2 )

topos = { 'latency': ( lambda: TopoLatency() ),
          'slow': ( lambda: TopoSlow() )
}
