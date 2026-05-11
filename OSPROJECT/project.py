import tkinter as tk
from tkinter import ttk, messagebox
from multiprocessing import Process, Pipe, Queue, Value, Lock
import multiprocessing
import time

# ---------------- PIPE PART ---------------- #
def pipe_process(conn):
    while True:
        msg = conn.recv()
        if msg == "STOP":
            break
        conn.send("Pipe got: " + msg)

# ---------------- MESSAGE QUEUE PART ---------------- #
def queue_process(q, log_q):
    while True:
        msg = q.get()
        if msg == "STOP":
            break
        log_q.put("Queue got: " + msg)

# ---------------- SHARED MEMORY PART ---------------- #
def shared_memory_process(value, lock, log_q):
    while True:
        time.sleep(1)
        with lock:
            v = value.value

        if v == -1:
            break

        if v != 0:
            log_q.put(f"Shared Memory value: {v}")

# ---------------- MAIN APP ---------------- #
class IPCApp:
    def __init__(self, root):
        self.root = root
        self.root.title("IPC Debugger (Simple Version)")
        self.root.geometry("650x450")

        self.mode = tk.StringVar(value="Pipe")

        # IPC variables
        self.parent_conn = None
        self.pipe_p = None

        self.q = Queue()
        self.log_q = Queue()
        self.queue_p = None

        self.shared_val = Value('i', 0)
        self.lock = Lock()
        self.shared_p = None

        self.build_ui()
        self.root.after(500, self.show_logs)

    # ---------------- UI ---------------- #
    def build_ui(self):
        top = tk.Frame(self.root)
        top.pack(pady=10)

        tk.Label(top, text="Choose IPC Mode:").pack(side=tk.LEFT)

        ttk.Combobox(
            top,
            textvariable=self.mode,
            values=["Pipe", "Message Queue", "Shared Memory"],
            width=18
        ).pack(side=tk.LEFT, padx=10)

        self.entry = tk.Entry(self.root, width=45)
        self.entry.pack(pady=10)

        btns = tk.Frame(self.root)
        btns.pack()

        tk.Button(btns, text="Start", command=self.start).pack(side=tk.LEFT, padx=5)
        tk.Button(btns, text="Send", command=self.send).pack(side=tk.LEFT, padx=5)
        tk.Button(btns, text="Stop", command=self.stop).pack(side=tk.LEFT, padx=5)

        self.text = tk.Text(self.root, height=18, width=75)
        self.text.pack(pady=10)

    # ---------------- LOG FUNCTION ---------------- #
    def log(self, msg):
        self.text.insert(tk.END, msg + "\n")
        self.text.see(tk.END)

    def show_logs(self):
        while not self.log_q.empty():
            self.log(self.log_q.get())

        self.root.after(500, self.show_logs)

    # ---------------- START IPC ---------------- #
    def start(self):
        mode = self.mode.get()
        self.log(f"Starting: {mode}")

        if mode == "Pipe":
            parent, child = Pipe()
            self.parent_conn = parent
            self.pipe_p = Process(target=pipe_process, args=(child,))
            self.pipe_p.start()

        elif mode == "Message Queue":
            self.q = Queue()
            self.queue_p = Process(target=queue_process, args=(self.q, self.log_q))
            self.queue_p.start()

        elif mode == "Shared Memory":
            self.shared_val.value = 0
            self.shared_p = Process(
                target=shared_memory_process,
                args=(self.shared_val, self.lock, self.log_q)
            )
            self.shared_p.start()

        self.log("IPC started ✔")

    # ---------------- SEND DATA ---------------- #
    def send(self):
        msg = self.entry.get()
        if not msg:
            messagebox.showwarning("Oops", "Please type something")
            return

        mode = self.mode.get()

        if mode == "Pipe":
            self.parent_conn.send(msg)
            self.log("Sent (Pipe): " + msg)

            if self.parent_conn.poll():
                self.log(self.parent_conn.recv())

        elif mode == "Message Queue":
            self.q.put(msg)
            self.log("Sent (Queue): " + msg)

        elif mode == "Shared Memory":
            try:
                num = int(msg)
                with self.lock:
                    self.shared_val.value = num
                self.log("Written (Shared Memory): " + str(num))
            except:
                self.log("Only numbers allowed in Shared Memory")

        self.entry.delete(0, tk.END)

    # ---------------- STOP EVERYTHING ---------------- #
    def stop(self):
        self.log("Stopping IPC...")

        try:
            if self.parent_conn:
                self.parent_conn.send("STOP")

            if self.pipe_p:
                self.pipe_p.terminate()

            if self.q:
                self.q.put("STOP")

            if self.queue_p:
                self.queue_p.terminate()

            if self.shared_p:
                with self.lock:
                    self.shared_val.value = -1
                self.shared_p.terminate()

        except:
            pass

        self.log("Stopped ✔")

# ---------------- RUN APP ---------------- #
if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")

    root = tk.Tk()
    app = IPCApp(root)
    root.mainloop()
    