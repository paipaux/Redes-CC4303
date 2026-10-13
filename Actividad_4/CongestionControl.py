class CongestionControl:
    def __init__(self, mss):
        self.current_state = False #F == slow start \ T == congestion avoidance
        self.MSS = mss
        self.cwnd = 1
        self.ssthresh = None

        def check_ssthresh():
            if self.current_state == False:
                if self.cwnd >= self.ssthresh:
                    self.current_state = True

    def get_cwnd(self):
        return self.cwnd

    def get_MSS_in_cwnd(self):
        return self.get_cwnd() // self.MSS

    def event_ack_received(self):
        if self.current_state == False:
            pass

    


