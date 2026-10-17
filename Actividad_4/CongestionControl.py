class CongestionControl:
    def __init__(self, mss):
        self.current_state = False #F == slow start \ T == congestion avoidance
        self.MSS = mss
        self.cwnd = mss
        self.ssthresh = None

    def get_cwnd(self):
        return int(self.cwnd)

    def get_MSS_in_cwnd(self):
        return self.get_cwnd() // self.MSS

    def get_ssthresh(self):
        return self.ssthresh

    def is_state_slow_start(self):
        state = self.current_state
        if state == False:
            return True
        else:
            return False

    def is_state_congestion_avoidance(self):
        state = self.current_state

        if state == True:
            return True
        else:
            return False

    def check_ssthresh(self):
        current_ssthresh = self.ssthresh
        if (self.is_state_slow_start() and self.ssthresh is not None and self.cwnd >= current_ssthresh):
                self.current_state = True

    def event_ack_received(self):
        if self.is_state_slow_start():
            self.cwnd += self.MSS
        else: # es congestion
            self.cwnd += self.MSS/self.get_MSS_in_cwnd()

        self.check_ssthresh()

    def event_timeout(self):
        if self.is_state_slow_start():
            # hay que ver el priemr timeout
            if self.ssthresh is None:
                self.ssthresh = self.MSS * 4
        else:
            self.ssthresh = int(self.cwnd // 2)
        
        self.cwnd = self.MSS
        self.current_state = False
        self.check_ssthresh()


    
    

    


