Add-Type -AssemblyName System.Drawing

$fontTitle = New-Object System.Drawing.Font("Segoe UI", [float]30, [System.Drawing.FontStyle]::Bold)
$fontSubtitle = New-Object System.Drawing.Font("Segoe UI", [float]16, [System.Drawing.FontStyle]::Regular)
$fontHeading = New-Object System.Drawing.Font("Segoe UI", [float]19, [System.Drawing.FontStyle]::Bold)
$fontBody = New-Object System.Drawing.Font("Segoe UI", [float]15, [System.Drawing.FontStyle]::Regular)
$fontBold = New-Object System.Drawing.Font("Segoe UI", [float]15, [System.Drawing.FontStyle]::Bold)
$fontBadge = New-Object System.Drawing.Font("Segoe UI", [float]12, [System.Drawing.FontStyle]::Bold)
$fontFooter = New-Object System.Drawing.Font("Segoe UI", [float]11, [System.Drawing.FontStyle]::Regular)

$colorBg = [System.Drawing.Color]::FromArgb(248, 250, 252) # Slate-50
$colorNavy = [System.Drawing.Color]::FromArgb(30, 58, 138)  # Blue-900
$colorBlue = [System.Drawing.Color]::FromArgb(37, 99, 235)  # Blue-600
$colorCardBg = [System.Drawing.Color]::White
$colorCardBorder = [System.Drawing.Color]::FromArgb(226, 232, 240)
$colorText = [System.Drawing.Color]::FromArgb(30, 41, 59)
$colorTextMuted = [System.Drawing.Color]::FromArgb(100, 116, 139)
$colorAmber = [System.Drawing.Color]::FromArgb(217, 119, 6)
$colorEmerald = [System.Drawing.Color]::FromArgb(5, 150, 105)

function Draw-BaseSlide($g, $title, $category, $slideNum) {
    # Background
    $bBg = New-Object System.Drawing.SolidBrush($colorBg)
    $g.FillRectangle($bBg, 0, 0, 1920, 1080)
    
    # Top bar
    $bNavy = New-Object System.Drawing.SolidBrush($colorNavy)
    $g.FillRectangle($bNavy, 0, 0, 1920, 120)
    
    # Header Accent line
    $bBlue = New-Object System.Drawing.SolidBrush($colorBlue)
    $g.FillRectangle($bBlue, 0, 120, 1920, 5)
    
    # Header Title
    $bWhite = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)
    $bAmber = New-Object System.Drawing.SolidBrush($colorAmber)
    $g.DrawString("TRANSITO TMS & SDI FACTURATIE", $fontBadge, $bAmber, [float]80, [float]25)
    $g.DrawString($title, $fontTitle, $bWhite, [float]80, [float]48)
    
    # Slide tag
    $bMutedWhite = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(203, 213, 225))
    $g.DrawString("SCENE $slideNum / 4 • $category", $fontBadge, $bMutedWhite, [float]1500, [float]50)
    
    # Footer
    $bMuted = New-Object System.Drawing.SolidBrush($colorTextMuted)
    $g.DrawString("Transito Intermediazioni S.r.l. • Vrachtbemiddeling & SDI Facturatie • Ad van der Meijs", $fontFooter, $bMuted, [float]80, [float]1040)
    
    # Avatar placeholder hint zone (lower right 440x520)
    $penDash = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(148, 163, 184), [float]2)
    $penDash.DashStyle = [System.Drawing.Drawing2D.DashStyle]::Dash
    $bAvatarHint = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(241, 245, 249))
    $g.FillRectangle($bAvatarHint, 1400, 500, 440, 510)
    $g.DrawRectangle($penDash, 1400, 500, 440, 510)
    $g.DrawString("[ Plaats Avatar Ad van der Meijs Hier ]", $fontBold, $bMuted, [float]1430, [float]740)
}

function Draw-Card($g, $x, $y, $w, $h, $title, $items, $accentColor) {
    $bCard = New-Object System.Drawing.SolidBrush($colorCardBg)
    $pBorder = New-Object System.Drawing.Pen($colorCardBorder, [float]2)
    $bAccent = New-Object System.Drawing.SolidBrush($accentColor)
    $bText = New-Object System.Drawing.SolidBrush($colorText)
    
    $g.FillRectangle($bCard, $x, $y, $w, $h)
    $g.DrawRectangle($pBorder, $x, $y, $w, $h)
    
    # Left accent bar
    $g.FillRectangle($bAccent, $x, $y, 8, $h)
    
    # Title
    $g.DrawString($title, $fontHeading, $bAccent, [float]($x + 25), [float]($y + 18))
    
    # Items
    $curY = $y + 60
    foreach ($item in $items) {
        $g.DrawString("- " + $item, $fontBody, $bText, [float]($x + 25), [float]$curY)
        $curY += 36
    }
}

# ==================== SLIDE 1 ====================
$bmp1 = New-Object System.Drawing.Bitmap(1920, 1080)
$g1 = [System.Drawing.Graphics]::FromImage($bmp1)
$g1.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g1.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit

Draw-BaseSlide $g1 "1. Doel & Het Italiaanse Bedrijfsmodel" "BEDRIJFSMODEL" 1

$items1 = @(
    "Gevestigd in Italië als erkend transportintermediair (procacciatore d'affari).",
    "Jij hebt géén eigen vrachtwagens en rijdt niet zelf.",
    "Je treedt op namens een vast partner-transportbedrijf.",
    "Volledige focus op vrachtbemiddeling, acquisitie en klantrelaties."
)
Draw-Card $g1 80 160 1260 220 "De Driehoeksverhouding in de Praktijk" $items1 $colorBlue

$items2 = @(
    "1. Verlader: Vraagt transport aan; accepteert jouw offerte; betaalt rechtstreeks aan vervoerder.",
    "2. Transportbedrijf: Voert de fysieke vrachtrit uit en factureert direct aan de verlader.",
    "3. Intermediair: Factureert bemiddelingsprovisie (10% of vast) aan het transportbedrijf via SDI."
)
Draw-Card $g1 80 410 1260 210 "Operationele & Financiële Geldstroom" $items2 $colorEmerald

$items3 = @(
    "Artikel 7-ter DPR 633/72: Btw-verlegd naar EU/NL partnerbedrijf (Natura N6).",
    "Artikel 9 DPR 633/72: Niet belastbaar (Non imponibile, Natura N3.2) bij internationaal vervoer.",
    "100% fiscaal sluitend conform de Italiaanse belastingdienst (Agenzia delle Entrate)."
)
Draw-Card $g1 80 650 1260 210 "Fiscale Vrijstellingen & Btw-verlegging" $items3 $colorAmber

$p1 = "G:\Mijn Drive\mijn gemini opslag\johan\Slide_1_Bedrijfsmodel.png"
$bmp1.Save($p1, [System.Drawing.Imaging.ImageFormat]::Png)
$g1.Dispose()
$bmp1.Dispose()
Write-Host "Slide 1 opgeslagen: $p1"

# ==================== SLIDE 2 ====================
$bmp2 = New-Object System.Drawing.Bitmap(1920, 1080)
$g2 = [System.Drawing.Graphics]::FromImage($bmp2)
$g2.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g2.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit

Draw-BaseSlide $g2 "2. Zero-External-Pip Systeemarchitectuur" "ARCHITECTUUR" 2

$itemsA = @(
    "Gebouwd op pure Python 3 Standard Library (geen afhankelijkheid van externe pip packages).",
    "Maximale stabiliteit en razendsnelle opstarttijden.",
    "Lokale SQLite3 database: alle ritten, facturen en provisies staan 100% veilig op eigen pc.",
    "Cloudflare HTTPS Tunnel: veilige versleutelde smartphone toegang zonder open routerpoorten."
)
Draw-Card $g2 80 160 1260 220 "Krachtige Technische Kern" $itemsA $colorBlue

$itemsB = @(
    "server.py: Centrale HTTP REST API backend & sessie-routing.",
    "database.py: Automatische databasemigraties, ritten, relaties en OIC-boekhouding.",
    "pdf_generator.py: Vector PDF 1.4 generator voor offertes en commissiefacturen.",
    "sdi_generator.py: FatturaPA FPR12 XML generator voor Italiaanse fiscus.",
    "email_sender.py: SMTP & PEC mailclient voor directe offerte- en factuurverzending."
)
Draw-Card $g2 80 410 1260 250 "Belangrijkste Backend Modules" $itemsB $colorEmerald

$itemsC = @(
    "Desktop Single Page App (static/index.html & app.js) met KPI-dashboards en Chart.js.",
    "Mobiele Progressive Web App (static/mobile.html & mobile.js) voor iPhone & Android."
)
Draw-Card $g2 80 690 1260 170 "Gebruikersinterfaces (Desktop & Mobiel)" $itemsC $colorNavy

$p2 = "G:\Mijn Drive\mijn gemini opslag\johan\Slide_2_Architectuur.png"
$bmp2.Save($p2, [System.Drawing.Imaging.ImageFormat]::Png)
$g2.Dispose()
$bmp2.Dispose()
Write-Host "Slide 2 opgeslagen: $p2"

# ==================== SLIDE 3 ====================
$bmp3 = New-Object System.Drawing.Bitmap(1920, 1080)
$g3 = [System.Drawing.Graphics]::FromImage($bmp3)
$g3.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g3.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit

Draw-BaseSlide $g3 "3. Elektronische Facturatie (SDI) & Boekhouding" "FACTURATIE & FISCO" 3

$itemsF1 = @(
    "1-Klik Facturatie: Ritten direct factureren of maandelijks verzamelen op één factuur.",
    "FatturaPA FPR12 XML: 100% valide XML gereed voor verzending via SDI.",
    "Automatische A4 Copia di Cortesia PDF met Italiaans-Nederlandse specificatie.",
    "SDI status-opvolging: Gegenereerd, Verzonden, Notifica di avvenuta consegna."
)
Draw-Card $g3 80 160 1260 220 "Fattura Elettronica & SDI Export" $itemsF1 $colorAmber

$itemsF2 = @(
    "Registro IVA Vendite (art. 23 DPR 633/72): Wettelijk verkoopregister van provisiefacturen.",
    "Registro IVA Acquisti (art. 25 DPR 633/72): Inkoopregister van bedrijfskosten.",
    "Liquidazione IVA & F24: Berekening periodiek btw-saldo (Codice Tributo 6031).",
    "Conto Economico & Balans: Winst- en verliesrekening ex art. 2425 Codice Civile met IRES & IRAP."
)
Draw-Card $g3 80 410 1260 230 "Italiaanse Boekhouding & Fiscale Registers" $itemsF2 $colorEmerald

$itemsF3 = @(
    "Percentage (bijv. 10%), Vaste Fee (bijv. € 200,- per rit), Marge of Vrije Invoer.",
    "Direct inzicht in verdiende netto bemiddelingsprovisies per week, maand en jaar."
)
Draw-Card $g3 80 670 1260 180 "4 Flexibele Provisiemodellen" $itemsF3 $colorBlue

$p3 = "G:\Mijn Drive\mijn gemini opslag\johan\Slide_3_SDI_Boekhouding.png"
$bmp3.Save($p3, [System.Drawing.Imaging.ImageFormat]::Png)
$g3.Dispose()
$bmp3.Dispose()
Write-Host "Slide 3 opgeslagen: $p3"

# ==================== SLIDE 4 ====================
$bmp4 = New-Object System.Drawing.Bitmap(1920, 1080)
$g4 = [System.Drawing.Graphics]::FromImage($bmp4)
$g4.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g4.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit

Draw-BaseSlide $g4 "4. Mobiele Smartphone App & Offerte Cyclus" "MOBIEL & CONNECTIVITEIT" 4

$itemsM1 = @(
    "Geoptimaliseerd voor smartphones (touch-targets van 48px+ en duidelijke knoppen).",
    "Onderweg direct ritten invoeren, vrachttarieven offreren en commissie berekenen.",
    "Directe download van A4 PDF vrachtofferte of delen via WhatsApp.",
    "Geen App Store vereist: installeerbaar via 'Zet op beginscherm' als PWA."
)
Draw-Card $g4 80 160 1260 220 "Mobiele PWA Smartphone App (/mobile)" $itemsM1 $colorBlue

$itemsM2 = @(
    "Automatische e-mailverzending van de vrachtofferte naar de klant én de administratie.",
    "Inclusief officiële A4 PDF bijlage met laad-/loslocaties en CMR-clausules.",
    "Ingebouwde persoonlijke videotoelichting van Ad van der Meijs direct in de e-mail."
)
Draw-Card $g4 80 410 1260 210 "Complete Offerte- & E-mailcyclus" $itemsM2 $colorAmber

$itemsM3 = @(
    "Transito Intermediazioni S.r.l. • Ad van der Meijs",
    "Veilig, stabiel, en 100% compliant met de Italiaanse en Europese wetgeving."
)
Draw-Card $g4 80 650 1260 180 "Klaar voor de Toekomst" $itemsM3 $colorNavy

$p4 = "G:\Mijn Drive\mijn gemini opslag\johan\Slide_4_Mobiel_PWA.png"
$bmp4.Save($p4, [System.Drawing.Imaging.ImageFormat]::Png)
$g4.Dispose()
$bmp4.Dispose()
Write-Host "Slide 4 opgeslagen: $p4"
