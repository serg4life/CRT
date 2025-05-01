from multiprocessing import Lock, Queue

class ContadorLocal:
    """Instancia de contador local"""
    
    def __init__(self, cola: Queue):
        self.valor = 0
        self._lock = Lock() # Lock interno
        self._cola = cola# Cola integrada

    def incrementar(self):
        with self._lock:
            self.valor += 1
            self._cola.put(self.valor)
            
    def decrementar(self):
        with self._lock:
            self.valor -= 1
            self._cola.put(self.valor)