import os
import subprocess
import sys
from PIL import Image

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, "assets")
    ico_path = os.path.join(assets_dir, "icon.ico")
    icns_path = os.path.join(assets_dir, "icon.icns")

    if not os.path.exists(ico_path):
        print(f"Error: {ico_path} does not exist.")
        sys.exit(1)

    print(f"Extracting images from {ico_path}...")
    try:
        img = Image.open(ico_path)
        
        # Determine the number of frames
        num_frames = getattr(img, "n_frames", 1)
        print(f"ICO has {num_frames} frames.")
        
        best_frame = 0
        largest_width = 0
        
        for frame in range(num_frames):
            img.seek(frame)
            w, h = img.size
            print(f"Frame {frame} size: {w}x{h}")
            if w > largest_width:
                largest_width = w
                best_frame = frame
                
        print(f"Using frame {best_frame} with largest width {largest_width}x{largest_width}")
        img.seek(best_frame)
        
        # Save as high-res PNG
        png_path = os.path.join(assets_dir, "icon_temp.png")
        rgba_img = img.convert("RGBA")
        rgba_img.save(png_path, "PNG")
        print(f"Temporary PNG saved to {png_path}")
        
        # Create iconset directory
        iconset_dir = os.path.join(assets_dir, "icon.iconset")
        os.makedirs(iconset_dir, exist_ok=True)
        
        # Standard macOS icon sizes required for .iconset
        icon_sizes = [
            (16, "icon_16x16.png"),
            (32, "icon_16x16@2x.png"),
            (32, "icon_32x32.png"),
            (64, "icon_32x32@2x.png"),
            (128, "icon_128x128.png"),
            (256, "icon_128x128@2x.png"),
            (256, "icon_256x256.png"),
            (512, "icon_256x256@2x.png"),
            (512, "icon_512x512.png"),
            (1024, "icon_512x512@2x.png"),
        ]
        
        for size, name in icon_sizes:
            resized = rgba_img.resize((size, size), Image.Resampling.LANCZOS)
            resized.save(os.path.join(iconset_dir, name))
            
        print("Generated iconset files. Running iconutil...")
        subprocess.run(["iconutil", "-c", "icns", iconset_dir, "-o", icns_path], check=True)
        print(f"Successfully generated macOS icon: {icns_path}")
        
        # Clean up
        os.remove(png_path)
        for size, name in icon_sizes:
            os.remove(os.path.join(iconset_dir, name))
        os.rmdir(iconset_dir)
        print("Cleanup completed.")
        
    except Exception as e:
        print(f"Failed to generate ICNS file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
