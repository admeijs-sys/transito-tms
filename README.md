# Transito - Transport Intermediair & SDI Facturatiesysteem 🤝🇮🇹

Een complete fullstack applicatie en mobiele smartphone-app speciaal ontworpen voor een **transportintermediair / vrachtmakelaar / agent** (*intermediario dei trasporti / procacciatore d'affari*) in Italië die optreedt namens een vast **partner-transportbedrijf**.

---

## 💡 Het Aangepaste Bedrijfs- en Facturatiemodel

In dit model voert jouw Italiaanse onderneming **zelf géén fysieke transporten uit** en bezit geen vrachtwagens. 

1. **De Verlader (Opdrachtgever)**:
   - Jouw bedrijf werft en bemiddelt de transportopdrachten bij fabrieken en verladers (bijv. in Italië, Nederland of Duitsland).
   - De verlader betaalt het volledige vrachttarief rechtstreeks aan het transportbedrijf.
2. **Het Partner Transportbedrijf (De Principal)**:
   - Voert het fysieke transport uit en factureert het transport rechtstreeks aan de verlader.
3. **Jouw Italiaanse Onderneming (De Intermediair)**:
   - Brengt een **bemiddelingscommissie (*provvigione di intermediazione*)** in rekening bij het transportbedrijf (bijv. standaard 10% van het vrachttarief of een vaste fee per bemiddelde rit).
   - Genereert officiële **FatturaPA XML commissiefacturen (FPR12)** voor het Italiaanse **Sistema di Interscambio (SDI)**.
   - **Btw-behandeling**:
     - Transportbedrijf in Nederland (EU): **Artikel 7-ter DPR 633/1972** &rarr; Btw-verlegd (*Inversione contabile*, Natura **`N6`**).
     - Transportbedrijf in Italië bij internationale vracht: **Artikel 9, c. 1, n. 7/9 DPR 633/1972** &rarr; *Non imponibile* (Natura **`N3.2`**).

---

## 🌟 Belangrijkste Functionaliteiten

### 1. Bemiddelde Opdrachtenbeheer
- **Dossiers**: Registratie van laad- en losadres, goederen, gewicht, laadmeters en CMR-referenties.
- **Vrachttarief & Provisiecalculatie**: Directe berekening van jouw provisie (€) op basis van het vrachttarief en commissiepercentage.
- **Statusflow**: *Aangemeld &rarr; Bevestigd door Vervoerder &rarr; Onderweg &rarr; Geleverd &rarr; Commissie Gefactureerd*.

### 2. SDI Commissiefacturatie (FatturaPA FPR12)
- **Per Rit of Verzamel-Commissiefactuur**: Factureer met 1 klik individuele ritten óf verzamel alle openstaande provisies van de maand op één officiële FatturaPA XML gericht aan het transportbedrijf.
- **XML Viewer & Download**: Bekijk de gegenereerde XML met syntax-markering of download het officiële `.xml` bestand.
- **SDI Gateway Simulatie**: Test en volg de status van verzonden commissiefacturen (*Consegnata*).

### 3. Italiaanse Boekhoudmodule (*Contabilità e Fisco Italiano*) 🏛️
- **Wettelijke Btw-registers (DPR 633/1972)**:
  - *Registro IVA Vendite (art. 23)*: Overzicht van uitgaande provisiefacturen met Natura-codes (N6, N3.2, 22%).
  - *Registro IVA Acquisti (art. 25)*: Registratie van inkomende bedrijfskosten (commercialista, software, telefoon, kantoor) met aftrekbare btw (*IVA detraibile*).
- **Liquidazione Periodica IVA (LIPE) & Modello F24**:
  - Automatische verrekening tussen *IVA a debito* en *IVA a credito*.
  - Weergave van het te betalen btw-saldo of btw-tegoed, inclusief Italiaanse belastingcode (*Codice Tributo 6031*).
- **Conto Economico (Winst- en Verliesrekening ex art. 2425 Codice Civile)**:
  - A) Valore della Produzione (bemiddelingsprovisies)
  - B) Costi della Produzione (diensten, software, bankkosten)
  - Verschil A - B (EBITDA / Bedrijfsresultaat)
  - Berekening van Italiaanse vennootschapsbelasting: **IRES (24%)** en **IRAP (3.9%)**
  - **Netto winst (*Utile netto d'esercizio*)**.
- **Stato Patrimoniale (Balans ex art. 2424 Codice Civile)**:
  - Activa: liquide middelen, openstaande provisie-vorderingen, btw-tegoed.
  - Passiva: gestort bedrijfskapitaal (**€ 100.000** wettelijke eis expediteur), winst, leveranciersschulden.
- **Piano dei Conti (Rekeningschema)**:
  - Italiaans standaard rekeningschema conform de OIC-richtlijnen.

### 4. Mobiele Smartphone-App (PWA) 📱
- Speciaal ontworpen mobiele interface (`/mobile`) om onderweg direct bemiddelingsopdrachten in te voeren.
- Toont direct: *"Jouw provisie: € 245,00 (10%)"*.
- Met 1 tik aangemeld en direct zichtbaar op kantoor en klaar voor het transportbedrijf!
- Te installeren op iPhone en Android via *"Zet op beginscherm"* (*Add to Home Screen*).

---

## 🚀 Starten

### Windows
Dubbelklik op:
```cmd
start.bat
```
Of via PowerShell:
```powershell
python server.py
```
- **Kantoor TMS (PC)**: [http://127.0.0.1:8080](http://127.0.0.1:8080)
- **Mobiele App (Telefoon)**: [http://192.168.68.104:8080/mobile](http://192.168.68.104:8080/mobile) (of scan de QR-code rechtsboven in het scherm).
