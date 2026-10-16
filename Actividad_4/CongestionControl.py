class CongestionControl:
    def __init__(self, mss):
        self.current_state = False #F == slow start \ T == congestion avoidance
        self.MSS = mss
        self.cwnd = mss
        self.ssthresh = None

    def check_ssthresh(self):
        print(self.ssthresh)
        current_ssthresh = self.ssthresh
        if self.current_state == False:
            if self.ssthresh == None:
                current_ssthresh = -1
            if self.cwnd >= current_ssthresh:
                self.current_state = True

    def get_cwnd(self):
        return self.cwnd

    def get_MSS_in_cwnd(self):
        return self.get_cwnd() // self.MSS

    def get_ssthresh(self):
        return self.ssthresh

    def event_ack_received(self):
        if self.current_state == False:
            current_cwnd = self.get_cwnd()
            self.cwnd = current_cwnd + self.MSS
            

        if self.current_state == True:
            current_cwnd = self.get_cwnd()
            self.cwnd = int(current_cwnd + (self.MSS/self.get_MSS_in_cwnd()))

        self.check_ssthresh()

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


    def event_timeout(self):
        if self.is_state_slow_start():
            self.ssthresh = self.MSS * 4
        self.check_ssthresh()


    
    

    


