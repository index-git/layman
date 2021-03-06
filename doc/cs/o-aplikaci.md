# O Laymanovi

## Úvod
Layman je služba pro publikování geoporostorových dat na webu prostřednictvím REST API. Layman přijímá vektorová data ve formátech GeoJSON nebo ShapeFile a spolu s vizuálním stylem je zpřístupňuje přes standardizovaná OGC rozhraní: Web Map Service, Web Feature Service a Catalogue Service. Layman umožňuje snadno publikovat i velké soubory dat, a to díky uploadu po částech a asynchronnímu zpracování.

## Nejdůležitější vlastnosti

### Vrstvy a mapy
Layman podporuje dva základní modely geoprostorových dat: vrstvy a mapy. **Vrstva** je tvořena kombinací vektorových dat (GeoJSON nebo ShapeFile) a vizualizace (SLD nebo SE styl). **Mapa** je kolekcí vrstev, která je popsána ve formátu JSON.


### Přístupnost
Existuje více klientských aplikací pro komunikaci s Laymanem prostřednictvím jeho REST API: jednoduchý testovací webový klient, desktopový klient v QGISu a knihovna HSLayers. Publikovaná data jsou přístupná přes standardizovaná OGC rozhraní: Web Map Service, Web Feature Service a Catalogue Service.

### Bezpečnost
Bezpečnostní systém Laymana využívá dvou známých konceptů: autentizace a autorizace. Běžná konfigurace sestává z autentizace založené na protokolu OAuth2 a autorizace zajišťující, že pouze vlastník dat má práva na jejich editaci.

### Škálovatelnost
Díky uploadu po částech lze snadno publikovat i velké soubory dat. Asynchronní zpracování zajišťuje rychlou komunikaci s REST API. Zpracování dat může být distribuováno na více serverů. Layman stojí na ramenou široce využívaných programů, mezi než patří Flask, PostgreSQL, PostGIS, GDAL, GeoServer, Celery a Redis.
