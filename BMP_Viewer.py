import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import math

class BMPParser:

    def __init__(self, bmp_bytes):

        self.bmp_bytes = bmp_bytes
        self.file_size = self._parse_file_size()
        self.width = self._parse_width()
        self.height = self._parse_height()
        self.bits_per_pixel = self._parse_bits_per_pixel()
        self.pixel_data_offset = self._parse_pixel_data_offset()
        self.color_table = self._parse_color_table()
        self.pixel_data = self._parse_pixel_data()

    def _parse_file_size(self):
        return int.from_bytes(self.bmp_bytes[2:6], 'little')
    
    def _parse_width(self):
        return int.from_bytes(self.bmp_bytes[18:22], 'little')
    
    def _parse_height(self):
        return int.from_bytes(self.bmp_bytes[22:26], 'little')
    
    def _parse_bits_per_pixel(self):
        return int.from_bytes(self.bmp_bytes[28:30], 'little')
    
    def _parse_pixel_data_offset(self):
        return int.from_bytes(self.bmp_bytes[10:14], 'little')
    
    def _parse_color_table(self):

        if self.bits_per_pixel in (1,4,8):
            header_size = int.from_bytes(self.bmp_bytes[14:18], 'little')
            color_table_offset = 14 + header_size

            if self.bits_per_pixel == 1:
                num_colors = 2

            elif self.bits_per_pixel == 4:
                num_colors = 16

            else:
                num_colors = 256
            
            color_table = []

            for i in range(num_colors):
                start = color_table_offset + (i * 4)
                if start + 3 >= len(self.bmp_bytes):
                    break
                b = self.bmp_bytes[start]
                g = self.bmp_bytes[start + 1]
                r = self.bmp_bytes[start + 2]
                color_table.append((r, g, b))
            return color_table
        return None

   
    def _parse_pixel_data(self):
        width = self.width
        height = abs(self.height)
        bpp = self.bits_per_pixel
        bytes_per_row = ((width * bpp + 31) // 32) * 4
        start_offset = self.pixel_data_offset
        pixel_data = self.bmp_bytes[start_offset:]
        rows = []
        for row_idx in range(height):
            row_start = row_idx * bytes_per_row
            row_end = row_start + bytes_per_row
            row_bytes = pixel_data[row_start:row_end]
            pixels = []
            if bpp == 24:
                for i in range(width):
                    pixel_start = i * 3
                    if pixel_start + 2 >= len(row_bytes):
                        break
                    b = row_bytes[pixel_start]
                    g = row_bytes[pixel_start + 1]
                    r = row_bytes[pixel_start + 2]
                    pixels.append((r, g, b))
            elif bpp == 8:
                color_table = self.color_table
                for i in range(width):
                    if i >= len(row_bytes):
                        break
                    index = row_bytes[i]
                    if index < len(color_table):
                        pixels.append(color_table[index])
                    else:
                        pixels.append((0, 0, 0))
            elif bpp == 4:
                color_table = self.color_table
                for i in range(len(row_bytes)):
                    byte = row_bytes[i]
                    high = (byte >> 4) & 0x0F
                    low = byte & 0x0F
                    pixels.extend([color_table[high], color_table[low]])
                pixels = pixels[:width]
            elif bpp == 1:
                color_table = self.color_table
                for byte in row_bytes:
                    for bit in range(7, -1, -1):
                        index = (byte >> bit) & 0x01
                        pixels.append(color_table[index])
                pixels = pixels[:width]
            else:
                raise ValueError(f"Unsupported BPP: {bpp}")
            rows.append(pixels)
        if self.height > 0:
            rows = rows[::-1]
        return rows
                
class UserInterface:
    
    def __init__(self, root):
        self.root = root
        self.original_rows = None
        self.photo_image = None
        self.brightness = 100
        self.scale = 100
        self.r_enabled = True
        self.g_enabled = True
        self.b_enabled = True
        self.create_widgets()

    def create_widgets(self):

        self.left_frame = tk.Frame(self.root)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        self.right_frame = tk.Frame(self.root)
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.open_button = tk.Button(self.left_frame, text="Open Image", command=self.open_file)
        self.open_button.pack(pady=(0, 10), fill=tk.X)

        self.meta_frame = tk.Frame(self.left_frame)
        self.meta_frame.pack(pady=(0, 10), fill=tk.X)

        self.file_size_label = tk.Label(self.meta_frame, text="File Size: ")
        self.file_size_label.pack(anchor="w")

        self.width_label = tk.Label(self.meta_frame, text="Width: ")
        self.width_label.pack(anchor="w")

        self.height_label = tk.Label(self.meta_frame, text="Height: ")
        self.height_label.pack(anchor="w")

        self.bpp_label = tk.Label(self.meta_frame, text="BPP: ")
        self.bpp_label.pack(anchor="w")

        self.brightness_slider = tk.Scale(self.left_frame, from_=0, to=200, orient=tk.HORIZONTAL, label="Brightness", command=self.update_brightness)
        self.brightness_slider.pack(pady=(0, 10), fill=tk.X)
        self.brightness_slider.set(100)

        self.scale_slider = tk.Scale(self.left_frame, from_=1, to=200, orient=tk.HORIZONTAL, label="Scale (%)", command=self.update_scale)
        self.scale_slider.set(100)
        self.scale_slider.pack(pady=(0, 10), fill=tk.X)

        self.rgb_frame = tk.Frame(self.left_frame)
        self.rgb_frame.pack(pady=(0, 10), fill=tk.X)

        self.r_button = tk.Button(self.rgb_frame, text="Disable Red", command=lambda: self.toggle_channel('r'), fg = "red")
        self.r_button.pack(fill=tk.X, pady=2)

        self.g_button = tk.Button(self.rgb_frame, text="Disable Green", command=lambda: self.toggle_channel('g'), fg = "green")
        self.g_button.pack(fill=tk.X, pady=2)

        self.b_button = tk.Button(self.rgb_frame, text="Disable Blue", command=lambda: self.toggle_channel('b'), fg = "blue")        
        self.b_button.pack(fill=tk.X, pady=2)

        self.reset_button = tk.Button(self.rgb_frame, text = "Reset Image", command=lambda: self.reset_image())
        self.reset_button.pack(fill=tk.X, pady=2)

        self.image_label = tk.Label(self.right_frame)
        self.image_label.pack(fill=tk.BOTH, expand=True)

    def open_file(self):

        file_path = filedialog.askopenfilename(filetypes=[("BMP files", "*.bmp")])
        if not file_path:
            return
        with open(file_path, "rb") as f:
            bmp_bytes = f.read()
        if bmp_bytes[:2] != b'BM':
            messagebox.showerror("Error", "Invalid BMP file")
            return
        
        parser = BMPParser(bmp_bytes)
        self.original_rows = parser.pixel_data
        self.file_size_label.config(text=f"File Size: {parser.file_size}")
        self.width_label.config(text=f"Width: {parser.width}")
        self.height_label.config(text=f"Height: {parser.height}")
        self.bpp_label.config(text=f"BPP: {parser.bits_per_pixel}")
        self.update_image()

    def update_brightness(self, value):

        self.brightness = int(value)
        self.update_image()

    def update_scale(self, value):

        self.scale = int(value)
        self.update_image()

    def update_rgb_buttons(self):

        self.r_button.config(text="Disable Red" if self.r_enabled else "Enable Red")
        self.g_button.config(text="Disable Green" if self.g_enabled else "Enable Green")
        self.b_button.config(text="Disable Blue" if self.b_enabled else "Enable Blue")

    def toggle_channel(self, channel):
        if channel == 'r':
            self.r_enabled = not self.r_enabled
        elif channel == 'g':
            self.g_enabled = not self.g_enabled
        elif channel == 'b':
            self.b_enabled = not self.b_enabled
        self.update_rgb_buttons()
        self.update_image()

    def reset_image(self):
        
        self.scale_slider.set(100)
        self.brightness_slider.set(100)


    def apply_brightness(self, rows):
        factor = self.brightness / 100.0
        adjusted = []
        for row in rows:
            new_row = []
            for r, g, b in row:
                new_r = int(r * factor)
                new_g = int(g * factor)
                new_b = int(b * factor)
                new_r = max(0, min(new_r, 255))
                new_g = max(0, min(new_g, 255))
                new_b = max(0, min(new_b, 255))
                new_row.append((new_r, new_g, new_b))
            adjusted.append(new_row)
        return adjusted

    def apply_scale(self, rows):
        scale = self.scale / 100.0
        original_height = len(rows)
        original_width = len(rows[0]) if original_height > 0 else 0
        new_width = max(1, int(original_width * scale))
        new_height = max(1, int(original_height * scale))
        scaled = []
        for y in range(new_height):
            src_y = y * original_height / new_height
            y0 = int(src_y)
            y1 = min(y0 + 1, original_height - 1)
            new_row = []
            for x in range(new_width):
                src_x = x * original_width / new_width
                x0 = int(src_x)
                x1 = min(x0 + 1, original_width - 1)
                r_sum, g_sum, b_sum, count = 0, 0, 0, 0
                for dy in [y0, y1]:
                    for dx in [x0, x1]:
                        if dy < original_height and dx < original_width:
                            r, g, b = rows[dy][dx]
                            r_sum += r
                            g_sum += g
                            b_sum += b
                            count += 1
                if count == 0:
                    new_pixel = (0, 0, 0)
                else:
                    new_pixel = (r_sum // count, g_sum // count, b_sum // count)
                new_row.append(new_pixel)
            scaled.append(new_row)
        return scaled

    def apply_rgb_toggles(self, rows):
        adjusted = []
        for row in rows:
            new_row = []
            for r, g, b in row:
                new_r = r if self.r_enabled else 0
                new_g = g if self.g_enabled else 0
                new_b = b if self.b_enabled else 0
                new_row.append((new_r, new_g, new_b))
            adjusted.append(new_row)
        return adjusted

    def update_image(self):
        if not self.original_rows:
            return
        bright = self.apply_brightness(self.original_rows)
        scaled = self.apply_scale(bright)
        toggled = self.apply_rgb_toggles(scaled)
        height = len(toggled)
        width = len(toggled[0]) if height > 0 else 0
        img_bytes = bytearray()
        for row in toggled:
            for r, g, b in row:
                img_bytes.extend([r, g, b])
        img = Image.frombytes('RGB', (width, height), bytes(img_bytes))
        self.photo_image = ImageTk.PhotoImage(img)
        self.image_label.config(image=self.photo_image)
        self.image_label.image = self.photo_image

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1920x1080")  
    root.title("View Image")
    app = UserInterface(root)
    root.mainloop()

   




            




