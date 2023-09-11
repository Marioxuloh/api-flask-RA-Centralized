import threading

#1            FIFO

class ClientResource_FIFO:
    def __init__(self, client_id):
        self.client_id = client_id
        self.sem = threading.Semaphore()

    def acquire_FIFO(self):

        try:
            acquired = self.sem.acquire(blocking=False)
            if not acquired:
                return False
            return True
        except Exception as e:
            print("ERROR acquiring resource:", str(e))
            return False

    def release_FIFO(self):

        try:
            self.sem.release() 
            return True
        except Exception as e:
            print("ERROR releasing resource:", str(e))
            return False      
        
#1            LAMPORT

class ClientResource_LAMPORT:
    def __init__(self, client_id):
        self.client_id = client_id
        self.sem = threading.Semaphore()
        self.sem_lamport_clock = threading.Semaphore()
        self.lamport_clock = {}

    def acquire_LAMPORT(self, id):

        if not self.sem_lamport_clock.acquire(timeout=5.0):
            raise RuntimeError('Timeout exceeded')
        try:
            self.lamport_clock[id] = self.lamport_clock.get(id, 0) + 1
            permissions = 0
            aux_id = 0

            for aux_id, aux_timestamp in self.lamport_clock.items():
                if(id != aux_id):
                    if (self.lamport_clock[id] < aux_timestamp):
                        permissions += permissions
                    elif(self.lamport_clock[id] > aux_timestamp):
                        if(aux_timestamp == -1):
                            permissions += permissions
                        else:
                            return False
                    else:
                        if(id < aux_id):
                            permissions += permissions

            if(permissions == len(self.lamport_clock) - 1):
                try:
                    acquired = self.sem.acquire(blocking=False)
                    if not acquired:
                        return False
                    return True
                except Exception as e:
                    print("ERROR acquiring resource:", str(e))
                return False
            else:
                return False
        finally:
            pass

    def release_LAMPORT(self, id):

        if not self.sem_lamport_clock.acquire(timeout=5.0):
            raise RuntimeError('Timeout exceeded')
        try:
            self.lamport_clock[id] = self.lamport_clock.get(id, 0) + 1
            try:
                self.sem.release() 
                return True
            except Exception as e:
                print("ERROR releasing resource:", str(e))
                return False      
        finally:
            pass

    def leave_LAMPORT(self, id):

        if not self.sem_lamport_clock.acquire(timeout=5.0):
            raise RuntimeError('Timeout exceeded')
        try:
            self.lamport_clock[id] = -1    
        finally:
            pass