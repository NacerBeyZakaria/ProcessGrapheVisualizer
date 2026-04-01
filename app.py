import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import networkx as nx



class SeqBlock:
    """Sequential block"""
    def __init__(self):
        self.items = []

class ParBlock:
    """Parallel block"""
    def __init__(self):
        self.branches = []

class Process:
    def __init__(self, name):
        self.name = name



class GraphBuilder:
    def __init__(self):
        self.edges = []
        self.nodes = set()

    def build(self, block, prev=None):
        if prev is None:
            prev = []

        last = prev

        for item in block.items:
            if isinstance(item, Process):
                self.nodes.add(item.name)
                for p in last:
                    self.edges.append((p, item.name))
                last = [item.name]

            elif isinstance(item, ParBlock):
                ends = []
                for branch in item.branches:
                    branch_end = self.build(branch, last.copy())
                    ends.extend(branch_end)
                last = ends

        return last




class ProcessGraphApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Parallel Process Graph Studio")
        self.root.geometry("1200x800")

        self.dragging_node = None

        main = ttk.Frame(root, padding=10)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="Process Graph Studio",
                  font=("Segoe UI", 16, "bold")).pack(pady=10)

        self.text = scrolledtext.ScrolledText(main, height=7, font=("Consolas", 11))
        self.text.pack(fill="x")

        self.text.insert("end",
"""S1;
parbegin
   P1;
   P2;
   parbegin P3; P4; parend;
parend;
S2;""")

        btns = ttk.Frame(main)
        btns.pack(pady=5)

        ttk.Button(btns, text="Visualize", command=self.visualize).grid(row=0,column=0,padx=5)
        ttk.Button(btns, text="Animate", command=self.animate).grid(row=0,column=1,padx=5)
        ttk.Button(btns, text="Highlight Critical Path", command=self.highlight_critical).grid(row=0,column=2,padx=5)
        ttk.Button(btns, text="Export PNG/PDF", command=self.export_graph).grid(row=0,column=3,padx=5)
        ttk.Button(btns, text="Generate Fork/Join", command=self.generate_fork_join).grid(row=0,column=4,padx=5)

        self.fig, self.ax = plt.subplots(figsize=(8,6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=main)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.canvas.mpl_connect("scroll_event", self.zoom)
        self.canvas.mpl_connect("button_press_event", self.start_drag)
        self.canvas.mpl_connect("motion_notify_event", self.drag)
        self.canvas.mpl_connect("button_release_event", self.stop_drag)

        self.positions = {}
        self.graph = nx.DiGraph()

    

    def parse_program(self, text):
            tokens = self.tokenize(text)

            root = SeqBlock()
            stack = [root]

            i = 0
            while i < len(tokens):
                tok = tokens[i]

              
                if tok == "begin":
                    seq = SeqBlock()
                    self._add_to_current(stack[-1], seq)
                    stack.append(seq)
                    i += 1
                    continue

                elif tok == "end":
                    if len(stack) == 1 or not isinstance(stack[-1], SeqBlock):
                        raise SyntaxError("Unexpected 'end'")
                    stack.pop()
                    i += 1
                    continue

              
                elif tok == "parbegin":
                    par = ParBlock()
                    self._add_to_current(stack[-1], par)

                    
                    branch = SeqBlock()
                    par.branches.append(branch)

                    stack.append(par)
                    stack.append(branch)

                    i += 1
                    continue

                elif tok == "|":   
                    if not isinstance(stack[-2], ParBlock):
                        raise SyntaxError("Branch separator outside parbegin")

                    stack.pop()  # finish current branch
                    new_branch = SeqBlock()
                    stack[-1].branches.append(new_branch)
                    stack.append(new_branch)

                    i += 1
                    continue

                elif tok == "parend":
                    if len(stack) < 2 or not isinstance(stack[-2], ParBlock):
                        raise SyntaxError("Unexpected 'parend'")

                    stack.pop()  
                    stack.pop()  
                    i += 1
                    continue

               
                elif tok == ";":
                    i += 1
                    continue

                
                else:
                    name = tok
                    proc = Process(name)
                    self._add_to_current(stack[-1], proc)
                    i += 1

            if len(stack) != 1:
                raise SyntaxError("Unmatched begin/parbegin block")

            return root
    
    def tokenize(self, text):
        text = text.replace(";", " ; ")
        text = text.replace("|", " | ")
        return text.split()
    
    def _add_to_current(self, current, item):
        if isinstance(current, SeqBlock):
            current.items.append(item)
        elif isinstance(current, ParBlock):
            current.branches[-1].items.append(item)
   

    def visualize(self):
        try:
            root = self.parse_program(self.text.get("1.0","end"))
            builder = GraphBuilder()
            builder.build(root)

            self.graph = nx.DiGraph()
            self.graph.add_nodes_from(builder.nodes)
            self.graph.add_edges_from(builder.edges)

            if not nx.is_directed_acyclic_graph(self.graph):
                raise ValueError("Cycle detected! Program must be acyclic.")

            
            levels = {}
            for node in nx.topological_sort(self.graph):
                preds = list(self.graph.predecessors(node))
                if not preds:
                    levels[node] = 0
                else:
                    levels[node] = max(levels[p] for p in preds) + 1

           
            layer_nodes = {}
            for node, lvl in levels.items():
                layer_nodes.setdefault(lvl, []).append(node)

            self.positions = {}
            for lvl, nodes in layer_nodes.items():
                width = len(nodes)
                for i, node in enumerate(nodes):
                    self.positions[node] = (i - width/2, -lvl)

            self.draw()

        except Exception as e:
            messagebox.showerror("Syntax Error", str(e))

    def draw(self, highlight=None):
        self.ax.clear()

        nx.draw_networkx_edges(self.graph, self.positions, ax=self.ax, arrows=True)

        node_colors = []
        for n in self.graph.nodes:
            if highlight and n in highlight:
                node_colors.append("orange")
            else:
                node_colors.append("#2E86DE")

        nx.draw_networkx_nodes(self.graph, self.positions,
                               node_color=node_colors,
                               node_size=2000,
                               ax=self.ax)

        nx.draw_networkx_labels(self.graph, self.positions, font_color="white", ax=self.ax)

        self.ax.axis("off")
        self.canvas.draw()



    def zoom(self, event):
        scale = 1.2 if event.button == 'up' else 0.8
        self.ax.set_xlim([x*scale for x in self.ax.get_xlim()])
        self.ax.set_ylim([y*scale for y in self.ax.get_ylim()])
        self.canvas.draw()



    def start_drag(self, event):
        for node, (x,y) in self.positions.items():
            if abs(event.xdata-x) < .05 and abs(event.ydata-y) < .05:
                self.dragging_node = node

    def drag(self, event):
        if self.dragging_node:
            self.positions[self.dragging_node] = (event.xdata, event.ydata)
            self.draw()

    def stop_drag(self, event):
        self.dragging_node = None



    def highlight_critical(self):
        path = nx.dag_longest_path(self.graph)
        self.draw(highlight=path)



    def animate(self):
        import time
        for node in nx.topological_sort(self.graph):
            self.draw(highlight=[node])
            self.root.update()
            time.sleep(0.6)
        self.draw()



    def export_graph(self):
        file = filedialog.asksaveasfilename(defaultextension=".png",
                                            filetypes=[("PNG","*.png"),("PDF","*.pdf")])
        if file:
            self.fig.savefig(file, bbox_inches='tight')



    def generate_fork_join(self):
        text = ""
        for node in nx.topological_sort(self.graph):
            preds = list(self.graph.predecessors(node))
            if len(preds) > 1:
                text += "join;\n"
            text += f"fork {node};\n"
        messagebox.showinfo("Fork/Join Code", text)



root = tk.Tk()
app = ProcessGraphApp(root)
root.mainloop()