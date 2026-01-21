import tkinter as tk

def main():
    root = tk.Tk()
    root.title("Tkinter Test")

    root.geometry("400x200")  # Optional: set window size

    label = tk.Label(root, text="Tkinter is working!", font=("Arial", 20))
    label.pack(expand=True)

    root.mainloop()

if __name__ == "__main__":
    main()
