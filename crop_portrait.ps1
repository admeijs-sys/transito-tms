Add-Type -AssemblyName System.Drawing

$srcPath = "G:\Mijn Drive\mijn gemini opslag\johan\presentator_foto.jpg"
$destPath = "G:\Mijn Drive\mijn gemini opslag\johan\presentator_portret.jpg"

$src = [System.Drawing.Bitmap]::FromFile($srcPath)
Write-Host "Originele afmetingen: $($src.Width) x $($src.Height)"

# Crop: focus on the face and chest, avoiding the side foreground figures
# The main person is roughly in the middle-right:
# X from ~15% to 85%, Y from 0% to 90%
$cropX = [int]($src.Width * 0.12)
$cropY = 0
$cropW = [int]($src.Width * 0.78)
$cropH = [int]($src.Height * 0.95)

$rect = New-Object System.Drawing.Rectangle $cropX, $cropY, $cropW, $cropH
$cropped = $src.Clone($rect, $src.PixelFormat)

$cropped.Save($destPath, [System.Drawing.Imaging.ImageFormat]::Jpeg)

$src.Dispose()
$cropped.Dispose()
Write-Host "Bijgesneden portret opgeslagen naar: $destPath"
