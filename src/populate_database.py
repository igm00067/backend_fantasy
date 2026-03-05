from app import create_app
from app.extensions import db
from app.models.competicion import Competicion
from app.models.equipo_real import EquipoReal
from app.models.jugador import Jugador
from app.models.usuario import Usuario

def populate_database():
    app = create_app()
    
    with app.app_context():
        print("🗑️  Limpiando datos existentes...")
        Jugador.query.delete()
        EquipoReal.query.delete()
        Competicion.query.delete()
        
        print("🏆 Creando competiciones...")
        
        laliga = Competicion(
            nombre='LaLiga EA Sports',
            pais='España',
            logo_url='https://upload.wikimedia.org/wikipedia/commons/thumb/1/13/LaLiga.svg/1200px-LaLiga.svg.png'
        )
        
        premier = Competicion(
            nombre='Premier League',
            pais='Inglaterra',
            logo_url='https://upload.wikimedia.org/wikipedia/en/thumb/f/f2/Premier_League_Logo.svg/1200px-Premier_League_Logo.svg.png'
        )
        
        db.session.add_all([laliga, premier])
        db.session.commit()
        
        print("⚽ Creando equipos de LaLiga...")
        
        # ========== LALIGA - 20 EQUIPOS ==========
        
        real_madrid = EquipoReal(nombre='Real Madrid', competicion_id=laliga.id, ciudad='Madrid')
        barcelona = EquipoReal(nombre='FC Barcelona', competicion_id=laliga.id, ciudad='Barcelona')
        atletico = EquipoReal(nombre='Atlético Madrid', competicion_id=laliga.id, ciudad='Madrid')
        athletic = EquipoReal(nombre='Athletic Club', competicion_id=laliga.id, ciudad='Bilbao')
        real_sociedad = EquipoReal(nombre='Real Sociedad', competicion_id=laliga.id, ciudad='San Sebastián')
        betis = EquipoReal(nombre='Real Betis', competicion_id=laliga.id, ciudad='Sevilla')
        villarreal = EquipoReal(nombre='Villarreal CF', competicion_id=laliga.id, ciudad='Villarreal')
        valencia = EquipoReal(nombre='Valencia CF', competicion_id=laliga.id, ciudad='Valencia')
        sevilla = EquipoReal(nombre='Sevilla FC', competicion_id=laliga.id, ciudad='Sevilla')
        girona = EquipoReal(nombre='Girona FC', competicion_id=laliga.id, ciudad='Girona')
        mallorca = EquipoReal(nombre='RCD Mallorca', competicion_id=laliga.id, ciudad='Palma')
        rayo = EquipoReal(nombre='Rayo Vallecano', competicion_id=laliga.id, ciudad='Madrid')
        celta = EquipoReal(nombre='Celta de Vigo', competicion_id=laliga.id, ciudad='Vigo')
        osasuna = EquipoReal(nombre='CA Osasuna', competicion_id=laliga.id, ciudad='Pamplona')
        getafe = EquipoReal(nombre='Getafe CF', competicion_id=laliga.id, ciudad='Getafe')
        espanyol = EquipoReal(nombre='RCD Espanyol', competicion_id=laliga.id, ciudad='Barcelona')
        alaves = EquipoReal(nombre='Deportivo Alavés', competicion_id=laliga.id, ciudad='Vitoria')
        valladolid = EquipoReal(nombre='Real Valladolid', competicion_id=laliga.id, ciudad='Valladolid')
        leganes = EquipoReal(nombre='CD Leganés', competicion_id=laliga.id, ciudad='Leganés')
        las_palmas = EquipoReal(nombre='UD Las Palmas', competicion_id=laliga.id, ciudad='Las Palmas')
        
        db.session.add_all([
            real_madrid, barcelona, atletico, athletic, real_sociedad, betis, villarreal, 
            valencia, sevilla, girona, mallorca, rayo, celta, osasuna, getafe, espanyol, 
            alaves, valladolid, leganes, las_palmas
        ])
        
        print("⚽ Creando equipos de Premier League...")
        
        # ========== PREMIER LEAGUE - 20 EQUIPOS ==========
        
        man_city = EquipoReal(nombre='Manchester City', competicion_id=premier.id, ciudad='Manchester')
        liverpool = EquipoReal(nombre='Liverpool FC', competicion_id=premier.id, ciudad='Liverpool')
        arsenal = EquipoReal(nombre='Arsenal FC', competicion_id=premier.id, ciudad='Londres')
        man_united = EquipoReal(nombre='Manchester United', competicion_id=premier.id, ciudad='Manchester')
        chelsea = EquipoReal(nombre='Chelsea FC', competicion_id=premier.id, ciudad='Londres')
        newcastle = EquipoReal(nombre='Newcastle United', competicion_id=premier.id, ciudad='Newcastle')
        tottenham = EquipoReal(nombre='Tottenham Hotspur', competicion_id=premier.id, ciudad='Londres')
        brighton = EquipoReal(nombre='Brighton & Hove Albion', competicion_id=premier.id, ciudad='Brighton')
        aston_villa = EquipoReal(nombre='Aston Villa', competicion_id=premier.id, ciudad='Birmingham')
        west_ham = EquipoReal(nombre='West Ham United', competicion_id=premier.id, ciudad='Londres')
        crystal_palace = EquipoReal(nombre='Crystal Palace', competicion_id=premier.id, ciudad='Londres')
        fulham = EquipoReal(nombre='Fulham FC', competicion_id=premier.id, ciudad='Londres')
        brentford = EquipoReal(nombre='Brentford FC', competicion_id=premier.id, ciudad='Londres')
        wolves = EquipoReal(nombre='Wolverhampton Wanderers', competicion_id=premier.id, ciudad='Wolverhampton')
        everton = EquipoReal(nombre='Everton FC', competicion_id=premier.id, ciudad='Liverpool')
        nottingham = EquipoReal(nombre='Nottingham Forest', competicion_id=premier.id, ciudad='Nottingham')
        bournemouth = EquipoReal(nombre='AFC Bournemouth', competicion_id=premier.id, ciudad='Bournemouth')
        leicester = EquipoReal(nombre='Leicester City', competicion_id=premier.id, ciudad='Leicester')
        ipswich = EquipoReal(nombre='Ipswich Town', competicion_id=premier.id, ciudad='Ipswich')
        southampton = EquipoReal(nombre='Southampton FC', competicion_id=premier.id, ciudad='Southampton')
        
        db.session.add_all([
            man_city, liverpool, arsenal, man_united, chelsea, newcastle, tottenham, brighton,
            aston_villa, west_ham, crystal_palace, fulham, brentford, wolves, everton,
            nottingham, bournemouth, leicester, ipswich, southampton
        ])
        
        db.session.commit()
        
        print("👤 Creando jugadores de LaLiga...")
        
        jugadores = []
        
        # ========== REAL MADRID ==========
        jugadores.extend([
            # Porteros
            Jugador(nombre='Thibaut Courtois', equipo_real_id=real_madrid.id, posicion='POR', precio=8.5,
                   velocidad=47, tiro=15, pase=31, regate=22, defensa=47, fisico=89, nacionalidad='Bélgica', edad=32),
            Jugador(nombre='Andriy Lunin', equipo_real_id=real_madrid.id, posicion='POR', precio=4.5,
                   velocidad=50, tiro=12, pase=35, regate=25, defensa=45, fisico=80, nacionalidad='Ucrania', edad=25),
            # Defensas
            Jugador(nombre='Dani Carvajal', equipo_real_id=real_madrid.id, posicion='DEF', precio=7.0,
                   velocidad=80, tiro=70, pase=75, regate=72, defensa=83, fisico=77, nacionalidad='España', edad=32),
            Jugador(nombre='Antonio Rüdiger', equipo_real_id=real_madrid.id, posicion='DEF', precio=8.0,
                   velocidad=78, tiro=55, pase=72, regate=66, defensa=86, fisico=85, nacionalidad='Alemania', edad=31),
            Jugador(nombre='Éder Militão', equipo_real_id=real_madrid.id, posicion='DEF', precio=8.5,
                   velocidad=83, tiro=58, pase=68, regate=70, defensa=85, fisico=84, nacionalidad='Brasil', edad=26),
            Jugador(nombre='Ferland Mendy', equipo_real_id=real_madrid.id, posicion='DEF', precio=6.5,
                   velocidad=88, tiro=52, pase=70, regate=76, defensa=82, fisico=78, nacionalidad='Francia', edad=29),
            Jugador(nombre='David Alaba', equipo_real_id=real_madrid.id, posicion='DEF', precio=7.5,
                   velocidad=79, tiro=72, pase=80, regate=78, defensa=84, fisico=76, nacionalidad='Austria', edad=32),
            Jugador(nombre='Lucas Vázquez', equipo_real_id=real_madrid.id, posicion='DEF', precio=5.0,
                   velocidad=82, tiro=68, pase=73, regate=75, defensa=75, fisico=72, nacionalidad='España', edad=33),
            # Centrocampistas
            Jugador(nombre='Jude Bellingham', equipo_real_id=real_madrid.id, posicion='MED', precio=12.0,
                   velocidad=82, tiro=82, pase=83, regate=85, defensa=78, fisico=84, nacionalidad='Inglaterra', edad=21),
            Jugador(nombre='Luka Modrić', equipo_real_id=real_madrid.id, posicion='MED', precio=7.5,
                   velocidad=74, tiro=78, pase=89, regate=87, defensa=72, fisico=65, nacionalidad='Croacia', edad=39),
            Jugador(nombre='Federico Valverde', equipo_real_id=real_madrid.id, posicion='MED', precio=9.5,
                   velocidad=87, tiro=82, pase=81, regate=80, defensa=79, fisico=85, nacionalidad='Uruguay', edad=26),
            Jugador(nombre='Eduardo Camavinga', equipo_real_id=real_madrid.id, posicion='MED', precio=8.0,
                   velocidad=86, tiro=70, pase=78, regate=82, defensa=80, fisico=77, nacionalidad='Francia', edad=22),
            Jugador(nombre='Aurélien Tchouaméni', equipo_real_id=real_madrid.id, posicion='MED', precio=8.5,
                   velocidad=78, tiro=75, pase=77, regate=74, defensa=84, fisico=86, nacionalidad='Francia', edad=24),
            Jugador(nombre='Dani Ceballos', equipo_real_id=real_madrid.id, posicion='MED', precio=5.5,
                   velocidad=76, tiro=72, pase=80, regate=82, defensa=68, fisico=70, nacionalidad='España', edad=28),
            # Delanteros
            Jugador(nombre='Kylian Mbappé', equipo_real_id=real_madrid.id, posicion='DEL', precio=15.0,
                   velocidad=97, tiro=89, pase=80, regate=92, defensa=36, fisico=77, nacionalidad='Francia', edad=26),
            Jugador(nombre='Vinícius Jr.', equipo_real_id=real_madrid.id, posicion='DEL', precio=13.0,
                   velocidad=95, tiro=80, pase=78, regate=90, defensa=29, fisico=67, nacionalidad='Brasil', edad=24),
            Jugador(nombre='Rodrygo', equipo_real_id=real_madrid.id, posicion='DEL', precio=10.0,
                   velocidad=91, tiro=80, pase=78, regate=85, defensa=33, fisico=65, nacionalidad='Brasil', edad=24),
            Jugador(nombre='Endrick', equipo_real_id=real_madrid.id, posicion='DEL', precio=7.0,
                   velocidad=88, tiro=78, pase=70, regate=82, defensa=30, fisico=72, nacionalidad='Brasil', edad=18),
            Jugador(nombre='Brahim Díaz', equipo_real_id=real_madrid.id, posicion='DEL', precio=6.5,
                   velocidad=85, tiro=75, pase=78, regate=86, defensa=32, fisico=64, nacionalidad='España', edad=25),
        ])
        
        # ========== FC BARCELONA ==========
        jugadores.extend([
            # Porteros
            Jugador(nombre='Marc-André ter Stegen', equipo_real_id=barcelona.id, posicion='POR', precio=8.0,
                   velocidad=45, tiro=13, pase=68, regate=26, defensa=50, fisico=87, nacionalidad='Alemania', edad=32),
            Jugador(nombre='Iñaki Peña', equipo_real_id=barcelona.id, posicion='POR', precio=3.5,
                   velocidad=48, tiro=11, pase=40, regate=22, defensa=42, fisico=75, nacionalidad='España', edad=25),
            # Defensas
            Jugador(nombre='Jules Koundé', equipo_real_id=barcelona.id, posicion='DEF', precio=8.5,
                   velocidad=88, tiro=60, pase=73, regate=74, defensa=84, fisico=82, nacionalidad='Francia', edad=26),
            Jugador(nombre='Ronald Araújo', equipo_real_id=barcelona.id, posicion='DEF', precio=8.0,
                   velocidad=82, tiro=62, pase=68, regate=65, defensa=86, fisico=87, nacionalidad='Uruguay', edad=25),
            Jugador(nombre='Andreas Christensen', equipo_real_id=barcelona.id, posicion='DEF', precio=6.5,
                   velocidad=74, tiro=55, pase=76, regate=68, defensa=82, fisico=78, nacionalidad='Dinamarca', edad=28),
            Jugador(nombre='Alejandro Balde', equipo_real_id=barcelona.id, posicion='DEF', precio=6.0,
                   velocidad=93, tiro=55, pase=72, regate=78, defensa=75, fisico=72, nacionalidad='España', edad=21),
            Jugador(nombre='Iñigo Martínez', equipo_real_id=barcelona.id, posicion='DEF', precio=5.5,
                   velocidad=68, tiro=58, pase=70, regate=62, defensa=83, fisico=80, nacionalidad='España', edad=33),
            # Centrocampistas
            Jugador(nombre='Pedri', equipo_real_id=barcelona.id, posicion='MED', precio=11.0,
                   velocidad=78, tiro=75, pase=87, regate=88, defensa=64, fisico=67, nacionalidad='España', edad=22),
            Jugador(nombre='Gavi', equipo_real_id=barcelona.id, posicion='MED', precio=9.0,
                   velocidad=82, tiro=72, pase=81, regate=84, defensa=73, fisico=72, nacionalidad='España', edad=20),
            Jugador(nombre='Frenkie de Jong', equipo_real_id=barcelona.id, posicion='MED', precio=10.0,
                   velocidad=85, tiro=73, pase=86, regate=86, defensa=77, fisico=78, nacionalidad='Países Bajos', edad=27),
            Jugador(nombre='Fermín López', equipo_real_id=barcelona.id, posicion='MED', precio=6.0,
                   velocidad=80, tiro=76, pase=78, regate=80, defensa=65, fisico=70, nacionalidad='España', edad=21),
            Jugador(nombre='Marc Casadó', equipo_real_id=barcelona.id, posicion='MED', precio=4.5,
                   velocidad=75, tiro=68, pase=75, regate=73, defensa=72, fisico=74, nacionalidad='España', edad=21),
            # Delanteros
            Jugador(nombre='Robert Lewandowski', equipo_real_id=barcelona.id, posicion='DEL', precio=11.0,
                   velocidad=78, tiro=92, pase=79, regate=86, defensa=44, fisico=82, nacionalidad='Polonia', edad=36),
            Jugador(nombre='Raphinha', equipo_real_id=barcelona.id, posicion='DEL', precio=9.0,
                   velocidad=88, tiro=81, pase=79, regate=85, defensa=38, fisico=70, nacionalidad='Brasil', edad=28),
            Jugador(nombre='Lamine Yamal', equipo_real_id=barcelona.id, posicion='DEL', precio=10.0,
                   velocidad=84, tiro=76, pase=80, regate=88, defensa=32, fisico=62, nacionalidad='España', edad=17),
            Jugador(nombre='Ferran Torres', equipo_real_id=barcelona.id, posicion='DEL', precio=7.5,
                   velocidad=86, tiro=80, pase=77, regate=81, defensa=35, fisico=70, nacionalidad='España', edad=24),
            Jugador(nombre='Ansu Fati', equipo_real_id=barcelona.id, posicion='DEL', precio=7.0,
                   velocidad=88, tiro=78, pase=74, regate=84, defensa=30, fisico=68, nacionalidad='España', edad=22),
        ])
        
        # ========== ATLÉTICO MADRID ==========
        jugadores.extend([
            # Portero
            Jugador(nombre='Jan Oblak', equipo_real_id=atletico.id, posicion='POR', precio=8.5,
                   velocidad=46, tiro=14, pase=45, regate=24, defensa=48, fisico=88, nacionalidad='Eslovenia', edad=31),
            # Defensas
            Jugador(nombre='José María Giménez', equipo_real_id=atletico.id, posicion='DEF', precio=7.0,
                   velocidad=76, tiro=60, pase=65, regate=63, defensa=85, fisico=84, nacionalidad='Uruguay', edad=29),
            Jugador(nombre='Mario Hermoso', equipo_real_id=atletico.id, posicion='DEF', precio=6.5,
                   velocidad=74, tiro=62, pase=73, regate=70, defensa=82, fisico=77, nacionalidad='España', edad=29),
            Jugador(nombre='Reinildo', equipo_real_id=atletico.id, posicion='DEF', precio=6.0,
                   velocidad=78, tiro=50, pase=62, regate=65, defensa=80, fisico=82, nacionalidad='Mozambique', edad=30),
            # Centrocampistas
            Jugador(nombre='Koke', equipo_real_id=atletico.id, posicion='MED', precio=7.0,
                   velocidad=72, tiro=74, pase=84, regate=78, defensa=76, fisico=73, nacionalidad='España', edad=32),
            Jugador(nombre='Marcos Llorente', equipo_real_id=atletico.id, posicion='MED', precio=8.5,
                   velocidad=90, tiro=78, pase=77, regate=79, defensa=75, fisico=82, nacionalidad='España', edad=29),
            Jugador(nombre='Rodrigo De Paul', equipo_real_id=atletico.id, posicion='MED', precio=7.5,
                   velocidad=80, tiro=75, pase=80, regate=82, defensa=70, fisico=76, nacionalidad='Argentina', edad=30),
            Jugador(nombre='Pablo Barrios', equipo_real_id=atletico.id, posicion='MED', precio=5.5,
                   velocidad=75, tiro=70, pase=76, regate=74, defensa=74, fisico=75, nacionalidad='España', edad=21),
            # Delanteros
            Jugador(nombre='Antoine Griezmann', equipo_real_id=atletico.id, posicion='DEL', precio=10.0,
                   velocidad=82, tiro=85, pase=84, regate=87, defensa=50, fisico=72, nacionalidad='Francia', edad=33),
            Jugador(nombre='Álvaro Morata', equipo_real_id=atletico.id, posicion='DEL', precio=8.5,
                   velocidad=84, tiro=82, pase=73, regate=78, defensa=40, fisico=80, nacionalidad='España', edad=32),
            Jugador(nombre='Ángel Correa', equipo_real_id=atletico.id, posicion='DEL', precio=7.0,
                   velocidad=85, tiro=77, pase=76, regate=84, defensa=38, fisico=68, nacionalidad='Argentina', edad=29),
        ])
        
        # ========== ATHLETIC CLUB ==========
        jugadores.extend([
            # Portero
            Jugador(nombre='Unai Simón', equipo_real_id=athletic.id, posicion='POR', precio=7.0,
                   velocidad=52, tiro=13, pase=58, regate=26, defensa=46, fisico=82, nacionalidad='España', edad=27),
            # Defensas
            Jugador(nombre='Yeray Álvarez', equipo_real_id=athletic.id, posicion='DEF', precio=6.0,
                   velocidad=70, tiro=55, pase=68, regate=62, defensa=81, fisico=79, nacionalidad='España', edad=29),
            Jugador(nombre='Dani Vivian', equipo_real_id=athletic.id, posicion='DEF', precio=6.5,
                   velocidad=74, tiro=58, pase=70, regate=65, defensa=80, fisico=80, nacionalidad='España', edad=25),
            Jugador(nombre='Yuri Berchiche', equipo_real_id=athletic.id, posicion='DEF', precio=5.5,
                   velocidad=76, tiro=60, pase=70, regate=68, defensa=77, fisico=74, nacionalidad='España', edad=34),
            # Centrocampistas
            Jugador(nombre='Oihan Sancet', equipo_real_id=athletic.id, posicion='MED', precio=8.0,
                   velocidad=76, tiro=78, pase=80, regate=82, defensa=62, fisico=72, nacionalidad='España', edad=24),
            Jugador(nombre='Iñaki Williams', equipo_real_id=athletic.id, posicion='MED', precio=7.5,
                   velocidad=94, tiro=74, pase=70, regate=77, defensa=45, fisico=78, nacionalidad='Ghana', edad=30),
            Jugador(nombre='Nico Williams', equipo_real_id=athletic.id, posicion='MED', precio=9.0,
                   velocidad=95, tiro=75, pase=76, regate=86, defensa=42, fisico=74, nacionalidad='España', edad=22),
            # Delantero
            Jugador(nombre='Gorka Guruzeta', equipo_real_id=athletic.id, posicion='DEL', precio=6.5,
                   velocidad=75, tiro=78, pase=68, regate=72, defensa=40, fisico=80, nacionalidad='España', edad=28),
        ])
        
        # ========== REAL SOCIEDAD ==========
        jugadores.extend([
            # Portero
            Jugador(nombre='Álex Remiro', equipo_real_id=real_sociedad.id, posicion='POR', precio=6.5,
                   velocidad=50, tiro=12, pase=52, regate=24, defensa=44, fisico=80, nacionalidad='España', edad=29),
            # Defensas
            Jugador(nombre='Igor Zubeldia', equipo_real_id=real_sociedad.id, posicion='DEF', precio=6.5,
                   velocidad=72, tiro=56, pase=72, regate=68, defensa=80, fisico=76, nacionalidad='España', edad=27),
            Jugador(nombre='Robin Le Normand', equipo_real_id=real_sociedad.id, posicion='DEF', precio=7.0,
                   velocidad=68, tiro=54, pase=70, regate=62, defensa=82, fisico=80, nacionalidad='Francia', edad=27),
            # Centrocampistas
            Jugador(nombre='Mikel Merino', equipo_real_id=real_sociedad.id, posicion='MED', precio=8.0,
                   velocidad=74, tiro=76, pase=80, regate=78, defensa=74, fisico=80, nacionalidad='España', edad=28),
            Jugador(nombre='Martín Zubimendi', equipo_real_id=real_sociedad.id, posicion='MED', precio=8.5,
                   velocidad=70, tiro=72, pase=82, regate=76, defensa=80, fisico=78, nacionalidad='España', edad=25),
            Jugador(nombre='Brais Méndez', equipo_real_id=real_sociedad.id, posicion='MED', precio=7.5,
                   velocidad=78, tiro=78, pase=80, regate=82, defensa=60, fisico=70, nacionalidad='España', edad=27),
            # Delanteros
            Jugador(nombre='Mikel Oyarzabal', equipo_real_id=real_sociedad.id, posicion='DEL', precio=8.5,
                   velocidad=80, tiro=80, pase=82, regate=84, defensa=48, fisico=70, nacionalidad='España', edad=27),
            Jugador(nombre='Takefusa Kubo', equipo_real_id=real_sociedad.id, posicion='DEL', precio=8.0,
                   velocidad=88, tiro=76, pase=78, regate=86, defensa=42, fisico=64, nacionalidad='Japón', edad=23),
        ])
        
        print("👤 Creando jugadores de Premier League...")
        
        # ========== MANCHESTER CITY ==========
        jugadores.extend([
            # Portero
            Jugador(nombre='Ederson', equipo_real_id=man_city.id, posicion='POR', precio=8.5,
                   velocidad=62, tiro=25, pase=87, regate=32, defensa=50, fisico=88, nacionalidad='Brasil', edad=31),
            # Defensas
            Jugador(nombre='Kyle Walker', equipo_real_id=man_city.id, posicion='DEF', precio=7.5,
                   velocidad=91, tiro=62, pase=76, regate=72, defensa=82, fisico=78, nacionalidad='Inglaterra', edad=34),
            Jugador(nombre='Rúben Dias', equipo_real_id=man_city.id, posicion='DEF', precio=9.0,
                   velocidad=62, tiro=52, pase=70, regate=63, defensa=88, fisico=84, nacionalidad='Portugal', edad=27),
            Jugador(nombre='John Stones', equipo_real_id=man_city.id, posicion='DEF', precio=8.0,
                   velocidad=72, tiro=62, pase=78, regate=70, defensa=84, fisico=80, nacionalidad='Inglaterra', edad=30),
            Jugador(nombre='Joško Gvardiol', equipo_real_id=man_city.id, posicion='DEF', precio=8.5,
                   velocidad=80, tiro=64, pase=75, regate=74, defensa=82, fisico=82, nacionalidad='Croacia', edad=22),
            # Centrocampistas
            Jugador(nombre='Kevin De Bruyne', equipo_real_id=man_city.id, posicion='MED', precio=13.0,
                   velocidad=76, tiro=88, pase=93, regate=87, defensa=64, fisico=78, nacionalidad='Bélgica', edad=33),
            Jugador(nombre='Rodri', equipo_real_id=man_city.id, posicion='MED', precio=10.0,
                   velocidad=62, tiro=76, pase=79, regate=72, defensa=84, fisico=85, nacionalidad='España', edad=28),
            Jugador(nombre='Phil Foden', equipo_real_id=man_city.id, posicion='MED', precio=11.0,
                   velocidad=85, tiro=82, pase=84, regate=88, defensa=55, fisico=70, nacionalidad='Inglaterra', edad=24),
            Jugador(nombre='Bernardo Silva', equipo_real_id=man_city.id, posicion='MED', precio=10.5,
                   velocidad=80, tiro=78, pase=86, regate=89, defensa=68, fisico=72, nacionalidad='Portugal', edad=30),
            Jugador(nombre='Mateo Kovačić', equipo_real_id=man_city.id, posicion='MED', precio=7.5,
                   velocidad=78, tiro=74, pase=82, regate=84, defensa=75, fisico=76, nacionalidad='Croacia', edad=30),
            # Delanteros
            Jugador(nombre='Erling Haaland', equipo_real_id=man_city.id, posicion='DEL', precio=15.0,
                   velocidad=89, tiro=92, pase=65, regate=80, defensa=45, fisico=88, nacionalidad='Noruega', edad=24),
            Jugador(nombre='Jack Grealish', equipo_real_id=man_city.id, posicion='DEL', precio=9.5,
                   velocidad=82, tiro=74, pase=82, regate=87, defensa=47, fisico=69, nacionalidad='Inglaterra', edad=29),
            Jugador(nombre='Jérémy Doku', equipo_real_id=man_city.id, posicion='DEL', precio=8.5,
                   velocidad=96, tiro=72, pase=74, regate=86, defensa=38, fisico=68, nacionalidad='Bélgica', edad=22),
        ])
        
        # ========== LIVERPOOL ==========
        jugadores.extend([
            # Portero
            Jugador(nombre='Alisson', equipo_real_id=liverpool.id, posicion='POR', precio=8.5,
                   velocidad=53, tiro=19, pase=79, regate=34, defensa=52, fisico=90, nacionalidad='Brasil', edad=32),
            # Defensas
            Jugador(nombre='Trent Alexander-Arnold', equipo_real_id=liverpool.id, posicion='DEF', precio=9.0,
                   velocidad=76, tiro=78, pase=89, regate=76, defensa=78, fisico=71, nacionalidad='Inglaterra', edad=26),
            Jugador(nombre='Virgil van Dijk', equipo_real_id=liverpool.id, posicion='DEF', precio=9.5,
                   velocidad=77, tiro=60, pase=71, regate=72, defensa=91, fisico=86, nacionalidad='Países Bajos', edad=33),
            Jugador(nombre='Ibrahima Konaté', equipo_real_id=liverpool.id, posicion='DEF', precio=8.0,
                   velocidad=82, tiro=54, pase=66, regate=65, defensa=84, fisico=86, nacionalidad='Francia', edad=25),
            Jugador(nombre='Andrew Robertson', equipo_real_id=liverpool.id, posicion='DEF', precio=7.5,
                   velocidad=84, tiro=66, pase=80, regate=74, defensa=80, fisico=77, nacionalidad='Escocia', edad=30),
            # Centrocampistas
            Jugador(nombre='Alexis Mac Allister', equipo_real_id=liverpool.id, posicion='MED', precio=8.5,
                   velocidad=76, tiro=76, pase=82, regate=81, defensa=72, fisico=75, nacionalidad='Argentina', edad=25),
            Jugador(nombre='Dominik Szoboszlai', equipo_real_id=liverpool.id, posicion='MED', precio=8.0,
                   velocidad=80, tiro=80, pase=82, regate=82, defensa=68, fisico=77, nacionalidad='Hungría', edad=24),
            Jugador(nombre='Curtis Jones', equipo_real_id=liverpool.id, posicion='MED', precio=6.5,
                   velocidad=78, tiro=72, pase=78, regate=80, defensa=65, fisico=70, nacionalidad='Inglaterra', edad=23),
            # Delanteros
            Jugador(nombre='Mohamed Salah', equipo_real_id=liverpool.id, posicion='DEL', precio=13.0,
                   velocidad=90, tiro=87, pase=81, regate=90, defensa=45, fisico=75, nacionalidad='Egipto', edad=32),
            Jugador(nombre='Darwin Núñez', equipo_real_id=liverpool.id, posicion='DEL', precio=10.0,
                   velocidad=88, tiro=82, pase=68, regate=78, defensa=37, fisico=80, nacionalidad='Uruguay', edad=25),
            Jugador(nombre='Luis Díaz', equipo_real_id=liverpool.id, posicion='DEL', precio=9.5,
                   velocidad=91, tiro=79, pase=78, regate=88, defensa=36, fisico=72, nacionalidad='Colombia', edad=27),
            Jugador(nombre='Cody Gakpo', equipo_real_id=liverpool.id, posicion='DEL', precio=8.5,
                   velocidad=86, tiro=80, pase=80, regate=83, defensa=40, fisico=76, nacionalidad='Países Bajos', edad=25),
        ])
        
        # ========== ARSENAL ==========
        jugadores.extend([
            # Portero
            Jugador(nombre='David Raya', equipo_real_id=arsenal.id, posicion='POR', precio=7.5,
                   velocidad=50, tiro=14, pase=62, regate=28, defensa=47, fisico=84, nacionalidad='España', edad=29),
            # Defensas
            Jugador(nombre='Ben White', equipo_real_id=arsenal.id, posicion='DEF', precio=7.5,
                   velocidad=82, tiro=64, pase=74, regate=72, defensa=80, fisico=76, nacionalidad='Inglaterra', edad=27),
            Jugador(nombre='William Saliba', equipo_real_id=arsenal.id, posicion='DEF', precio=8.5,
                   velocidad=80, tiro=56, pase=70, regate=68, defensa=85, fisico=82, nacionalidad='Francia', edad=23),
            Jugador(nombre='Gabriel Magalhães', equipo_real_id=arsenal.id, posicion='DEF', precio=8.0,
                   velocidad=72, tiro=62, pase=68, regate=64, defensa=84, fisico=84, nacionalidad='Brasil', edad=26),
            Jugador(nombre='Oleksandr Zinchenko', equipo_real_id=arsenal.id, posicion='DEF', precio=6.5,
                   velocidad=76, tiro=68, pase=80, regate=78, defensa=74, fisico=70, nacionalidad='Ucrania', edad=28),
            # Centrocampistas
            Jugador(nombre='Martin Ødegaard', equipo_real_id=arsenal.id, posicion='MED', precio=10.5,
                   velocidad=78, tiro=82, pase=88, regate=86, defensa=68, fisico=72, nacionalidad='Noruega', edad=25),
            Jugador(nombre='Declan Rice', equipo_real_id=arsenal.id, posicion='MED', precio=10.0,
                   velocidad=76, tiro=74, pase=82, regate=76, defensa=82, fisico=82, nacionalidad='Inglaterra', edad=25),
            Jugador(nombre='Kai Havertz', equipo_real_id=arsenal.id, posicion='MED', precio=9.0,
                   velocidad=80, tiro=80, pase=82, regate=82, defensa=60, fisico=76, nacionalidad='Alemania', edad=25),
            Jugador(nombre='Thomas Partey', equipo_real_id=arsenal.id, posicion='MED', precio=7.0,
                   velocidad=74, tiro=72, pase=76, regate=74, defensa=80, fisico=80, nacionalidad='Ghana', edad=31),
            # Delanteros
            Jugador(nombre='Bukayo Saka', equipo_real_id=arsenal.id, posicion='DEL', precio=11.0,
                   velocidad=88, tiro=82, pase=82, regate=87, defensa=52, fisico=72, nacionalidad='Inglaterra', edad=23),
            Jugador(nombre='Gabriel Martinelli', equipo_real_id=arsenal.id, posicion='DEL', precio=9.5,
                   velocidad=90, tiro=78, pase=76, regate=84, defensa=48, fisico=70, nacionalidad='Brasil', edad=23),
            Jugador(nombre='Gabriel Jesus', equipo_real_id=arsenal.id, posicion='DEL', precio=9.0,
                   velocidad=86, tiro=80, pase=78, regate=84, defensa=42, fisico=74, nacionalidad='Brasil', edad=27),
            Jugador(nombre='Leandro Trossard', equipo_real_id=arsenal.id, posicion='DEL', precio=8.0,
                   velocidad=84, tiro=78, pase=80, regate=82, defensa=46, fisico=68, nacionalidad='Bélgica', edad=29),
        ])
        
        # ========== MANCHESTER UNITED ==========
        jugadores.extend([
            # Portero
            Jugador(nombre='André Onana', equipo_real_id=man_united.id, posicion='POR', precio=7.5,
                   velocidad=58, tiro=18, pase=78, regate=34, defensa=46, fisico=85, nacionalidad='Camerún', edad=28),
            # Defensas
            Jugador(nombre='Diogo Dalot', equipo_real_id=man_united.id, posicion='DEF', precio=6.5,
                   velocidad=82, tiro=68, pase=72, regate=74, defensa=76, fisico=74, nacionalidad='Portugal', edad=25),
            Jugador(nombre='Lisandro Martínez', equipo_real_id=man_united.id, posicion='DEF', precio=8.0,
                   velocidad=75, tiro=58, pase=74, regate=70, defensa=84, fisico=78, nacionalidad='Argentina', edad=26),
            Jugador(nombre='Raphaël Varane', equipo_real_id=man_united.id, posicion='DEF', precio=7.0,
                   velocidad=78, tiro=52, pase=68, regate=64, defensa=86, fisico=80, nacionalidad='Francia', edad=31),
            Jugador(nombre='Luke Shaw', equipo_real_id=man_united.id, posicion='DEF', precio=6.5,
                   velocidad=78, tiro=64, pase=74, regate=72, defensa=78, fisico=74, nacionalidad='Inglaterra', edad=29),
            # Centrocampistas
            Jugador(nombre='Bruno Fernandes', equipo_real_id=man_united.id, posicion='MED', precio=10.5,
                   velocidad=78, tiro=84, pase=87, regate=82, defensa=62, fisico=76, nacionalidad='Portugal', edad=30),
            Jugador(nombre='Casemiro', equipo_real_id=man_united.id, posicion='MED', precio=8.0,
                   velocidad=66, tiro=70, pase=74, regate=68, defensa=84, fisico=84, nacionalidad='Brasil', edad=32),
            Jugador(nombre='Mason Mount', equipo_real_id=man_united.id, posicion='MED', precio=7.5,
                   velocidad=78, tiro=76, pase=80, regate=80, defensa=62, fisico=70, nacionalidad='Inglaterra', edad=25),
            Jugador(nombre='Kobbie Mainoo', equipo_real_id=man_united.id, posicion='MED', precio=5.5,
                   velocidad=74, tiro=68, pase=74, regate=76, defensa=70, fisico=72, nacionalidad='Inglaterra', edad=19),
            # Delanteros
            Jugador(nombre='Marcus Rashford', equipo_real_id=man_united.id, posicion='DEL', precio=10.0,
                   velocidad=92, tiro=82, pase=76, regate=84, defensa=40, fisico=76, nacionalidad='Inglaterra', edad=27),
            Jugador(nombre='Rasmus Højlund', equipo_real_id=man_united.id, posicion='DEL', precio=8.5,
                   velocidad=86, tiro=80, pase=68, regate=74, defensa=38, fisico=82, nacionalidad='Dinamarca', edad=21),
            Jugador(nombre='Alejandro Garnacho', equipo_real_id=man_united.id, posicion='DEL', precio=7.5,
                   velocidad=90, tiro=74, pase=72, regate=82, defensa=36, fisico=68, nacionalidad='Argentina', edad=20),
        ])
        
        # ========== CHELSEA ==========
        jugadores.extend([
            # Portero
            Jugador(nombre='Robert Sánchez', equipo_real_id=chelsea.id, posicion='POR', precio=6.0,
                   velocidad=52, tiro=15, pase=56, regate=28, defensa=44, fisico=82, nacionalidad='España', edad=26),
            # Defensas
            Jugador(nombre='Reece James', equipo_real_id=chelsea.id, posicion='DEF', precio=8.0,
                   velocidad=84, tiro=76, pase=78, regate=76, defensa=80, fisico=78, nacionalidad='Inglaterra', edad=24),
            Jugador(nombre='Thiago Silva', equipo_real_id=chelsea.id, posicion='DEF', precio=6.5,
                   velocidad=62, tiro=50, pase=72, regate=64, defensa=88, fisico=74, nacionalidad='Brasil', edad=40),
            Jugador(nombre='Levi Colwill', equipo_real_id=chelsea.id, posicion='DEF', precio=6.5,
                   velocidad=76, tiro=54, pase=68, regate=66, defensa=78, fisico=76, nacionalidad='Inglaterra', edad=21),
            Jugador(nombre='Ben Chilwell', equipo_real_id=chelsea.id, posicion='DEF', precio=7.0,
                   velocidad=82, tiro=68, pase=76, regate=74, defensa=76, fisico=74, nacionalidad='Inglaterra', edad=28),
            # Centrocampistas
            Jugador(nombre='Enzo Fernández', equipo_real_id=chelsea.id, posicion='MED', precio=9.5,
                   velocidad=76, tiro=78, pase=84, regate=82, defensa=72, fisico=74, nacionalidad='Argentina', edad=23),
            Jugador(nombre='Moisés Caicedo', equipo_real_id=chelsea.id, posicion='MED', precio=8.5,
                   velocidad=80, tiro=72, pase=76, regate=76, defensa=80, fisico=80, nacionalidad='Ecuador', edad=23),
            Jugador(nombre='Conor Gallagher', equipo_real_id=chelsea.id, posicion='MED', precio=7.0,
                   velocidad=78, tiro=74, pase=76, regate=76, defensa=74, fisico=76, nacionalidad='Inglaterra', edad=24),
            Jugador(nombre='Cole Palmer', equipo_real_id=chelsea.id, posicion='MED', precio=9.0,
                   velocidad=78, tiro=80, pase=82, regate=84, defensa=50, fisico=68, nacionalidad='Inglaterra', edad=22),
            # Delanteros
            Jugador(nombre='Nicolas Jackson', equipo_real_id=chelsea.id, posicion='DEL', precio=8.0,
                   velocidad=88, tiro=76, pase=70, regate=78, defensa=38, fisico=78, nacionalidad='Senegal', edad=23),
            Jugador(nombre='Raheem Sterling', equipo_real_id=chelsea.id, posicion='DEL', precio=8.5,
                   velocidad=88, tiro=78, pase=78, regate=85, defensa=42, fisico=70, nacionalidad='Inglaterra', edad=30),
            Jugador(nombre='Mykhailo Mudryk', equipo_real_id=chelsea.id, posicion='DEL', precio=7.5,
                   velocidad=94, tiro=72, pase=74, regate=82, defensa=36, fisico=68, nacionalidad='Ucrania', edad=23),
        ])
        
        # ========== NEWCASTLE UNITED ==========
        jugadores.extend([
            # Portero
            Jugador(nombre='Nick Pope', equipo_real_id=newcastle.id, posicion='POR', precio=6.5,
                   velocidad=48, tiro=16, pase=48, regate=22, defensa=46, fisico=84, nacionalidad='Inglaterra', edad=32),
            # Defensas
            Jugador(nombre='Kieran Trippier', equipo_real_id=newcastle.id, posicion='DEF', precio=7.0,
                   velocidad=74, tiro=72, pase=84, regate=72, defensa=78, fisico=72, nacionalidad='Inglaterra', edad=34),
            Jugador(nombre='Sven Botman', equipo_real_id=newcastle.id, posicion='DEF', precio=7.5,
                   velocidad=74, tiro=54, pase=68, regate=64, defensa=82, fisico=80, nacionalidad='Países Bajos', edad=24),
            Jugador(nombre='Fabian Schär', equipo_real_id=newcastle.id, posicion='DEF', precio=6.0,
                   velocidad=70, tiro=68, pase=70, regate=62, defensa=80, fisico=78, nacionalidad='Suiza', edad=32),
            Jugador(nombre='Dan Burn', equipo_real_id=newcastle.id, posicion='DEF', precio=5.5,
                   velocidad=64, tiro=50, pase=64, regate=58, defensa=78, fisico=80, nacionalidad='Inglaterra', edad=32),
            # Centrocampistas
            Jugador(nombre='Bruno Guimarães', equipo_real_id=newcastle.id, posicion='MED', precio=9.0,
                   velocidad=78, tiro=76, pase=80, regate=80, defensa=78, fisico=78, nacionalidad='Brasil', edad=26),
            Jugador(nombre='Sandro Tonali', equipo_real_id=newcastle.id, posicion='MED', precio=8.5,
                   velocidad=76, tiro=72, pase=80, regate=78, defensa=76, fisico=76, nacionalidad='Italia', edad=24),
            Jugador(nombre='Joelinton', equipo_real_id=newcastle.id, posicion='MED', precio=7.0,
                   velocidad=76, tiro=70, pase=72, regate=74, defensa=74, fisico=82, nacionalidad='Brasil', edad=28),
            # Delanteros
            Jugador(nombre='Alexander Isak', equipo_real_id=newcastle.id, posicion='DEL', precio=10.0,
                   velocidad=88, tiro=82, pase=74, regate=82, defensa=40, fisico=78, nacionalidad='Suecia', edad=25),
            Jugador(nombre='Callum Wilson', equipo_real_id=newcastle.id, posicion='DEL', precio=8.0,
                   velocidad=82, tiro=80, pase=70, regate=76, defensa=38, fisico=78, nacionalidad='Inglaterra', edad=32),
            Jugador(nombre='Anthony Gordon', equipo_real_id=newcastle.id, posicion='DEL', precio=7.5,
                   velocidad=86, tiro=74, pase=74, regate=80, defensa=44, fisico=68, nacionalidad='Inglaterra', edad=23),
        ])
        
        # ========== TOTTENHAM HOTSPUR ==========
        jugadores.extend([
            # Portero
            Jugador(nombre='Guglielmo Vicario', equipo_real_id=tottenham.id, posicion='POR', precio=6.0,
                   velocidad=54, tiro=14, pase=52, regate=26, defensa=44, fisico=80, nacionalidad='Italia', edad=28),
            # Defensas
            Jugador(nombre='Pedro Porro', equipo_real_id=tottenham.id, posicion='DEF', precio=7.0,
                   velocidad=80, tiro=70, pase=76, regate=74, defensa=74, fisico=72, nacionalidad='España', edad=25),
            Jugador(nombre='Cristian Romero', equipo_real_id=tottenham.id, posicion='DEF', precio=8.0,
                   velocidad=76, tiro=58, pase=68, regate=66, defensa=84, fisico=82, nacionalidad='Argentina', edad=26),
            Jugador(nombre='Micky van de Ven', equipo_real_id=tottenham.id, posicion='DEF', precio=7.5,
                   velocidad=94, tiro=52, pase=66, regate=68, defensa=78, fisico=78, nacionalidad='Países Bajos', edad=23),
            Jugador(nombre='Destiny Udogie', equipo_real_id=tottenham.id, posicion='DEF', precio=6.5,
                   velocidad=88, tiro=60, pase=68, regate=74, defensa=72, fisico=72, nacionalidad='Italia', edad=21),
            # Centrocampistas
            Jugador(nombre='James Maddison', equipo_real_id=tottenham.id, posicion='MED', precio=9.0,
                   velocidad=76, tiro=80, pase=86, regate=84, defensa=56, fisico=68, nacionalidad='Inglaterra', edad=28),
            Jugador(nombre='Yves Bissouma', equipo_real_id=tottenham.id, posicion='MED', precio=6.5,
                   velocidad=78, tiro=68, pase=72, regate=74, defensa=78, fisico=78, nacionalidad='Mali', edad=28),
            Jugador(nombre='Pape Matar Sarr', equipo_real_id=tottenham.id, posicion='MED', precio=6.0,
                   velocidad=80, tiro=68, pase=72, regate=74, defensa=72, fisico=76, nacionalidad='Senegal', edad=22),
            Jugador(nombre='Dejan Kulusevski', equipo_real_id=tottenham.id, posicion='MED', precio=8.5,
                   velocidad=82, tiro=78, pase=80, regate=84, defensa=52, fisico=74, nacionalidad='Suecia', edad=24),
            # Delanteros
            Jugador(nombre='Son Heung-min', equipo_real_id=tottenham.id, posicion='DEL', precio=11.0,
                   velocidad=88, tiro=86, pase=80, regate=86, defensa=45, fisico=74, nacionalidad='Corea del Sur', edad=32),
            Jugador(nombre='Richarlison', equipo_real_id=tottenham.id, posicion='DEL', precio=8.0,
                   velocidad=84, tiro=78, pase=72, regate=78, defensa=46, fisico=80, nacionalidad='Brasil', edad=27),
            Jugador(nombre='Brennan Johnson', equipo_real_id=tottenham.id, posicion='DEL', precio=7.0,
                   velocidad=90, tiro=74, pase=72, regate=78, defensa=42, fisico=70, nacionalidad='Gales', edad=23),
        ])
        
        # ========== ASTON VILLA ==========
        jugadores.extend([
            # Portero
            Jugador(nombre='Emiliano Martínez', equipo_real_id=aston_villa.id, posicion='POR', precio=7.5,
                   velocidad=52, tiro=17, pase=54, regate=28, defensa=48, fisico=86, nacionalidad='Argentina', edad=32),
            # Defensas
            Jugador(nombre='Matty Cash', equipo_real_id=aston_villa.id, posicion='DEF', precio=6.0,
                   velocidad=82, tiro=62, pase=68, regate=70, defensa=76, fisico=74, nacionalidad='Polonia', edad=27),
            Jugador(nombre='Ezri Konsa', equipo_real_id=aston_villa.id, posicion='DEF', precio=6.5,
                   velocidad=74, tiro=52, pase=66, regate=62, defensa=80, fisico=78, nacionalidad='Inglaterra', edad=27),
            Jugador(nombre='Pau Torres', equipo_real_id=aston_villa.id, posicion='DEF', precio=7.0,
                   velocidad=72, tiro=56, pase=74, regate=68, defensa=82, fisico=76, nacionalidad='España', edad=27),
            Jugador(nombre='Lucas Digne', equipo_real_id=aston_villa.id, posicion='DEF', precio=6.0,
                   velocidad=76, tiro=68, pase=78, regate=72, defensa=74, fisico=72, nacionalidad='Francia', edad=31),
            # Centrocampistas
            Jugador(nombre='Douglas Luiz', equipo_real_id=aston_villa.id, posicion='MED', precio=8.0,
                   velocidad=74, tiro=74, pase=78, regate=78, defensa=76, fisico=76, nacionalidad='Brasil', edad=26),
            Jugador(nombre='John McGinn', equipo_real_id=aston_villa.id, posicion='MED', precio=7.0,
                   velocidad=76, tiro=74, pase=76, regate=74, defensa=74, fisico=78, nacionalidad='Escocia', edad=30),
            Jugador(nombre='Boubacar Kamara', equipo_real_id=aston_villa.id, posicion='MED', precio=6.5,
                   velocidad=72, tiro=64, pase=74, regate=70, defensa=78, fisico=78, nacionalidad='Francia', edad=24),
            # Delanteros
            Jugador(nombre='Ollie Watkins', equipo_real_id=aston_villa.id, posicion='DEL', precio=9.5,
                   velocidad=88, tiro=80, pase=76, regate=80, defensa=42, fisico=76, nacionalidad='Inglaterra', edad=29),
            Jugador(nombre='Leon Bailey', equipo_real_id=aston_villa.id, posicion='DEL', precio=7.5,
                   velocidad=92, tiro=76, pase=74, regate=82, defensa=38, fisico=70, nacionalidad='Jamaica', edad=27),
            Jugador(nombre='Moussa Diaby', equipo_real_id=aston_villa.id, posicion='DEL', precio=8.0,
                   velocidad=90, tiro=74, pase=76, regate=84, defensa=40, fisico=68, nacionalidad='Francia', edad=25),
        ])
        
        db.session.add_all(jugadores)
        db.session.commit()
        
        print(f"✅ Base de datos poblada exitosamente!")
        print(f"   - {Competicion.query.count()} competiciones")
        print(f"   - {EquipoReal.query.count()} equipos reales")
        print(f"   - {Jugador.query.count()} jugadores")
        print(f"   - {Usuario.query.count()} usuarios")

if __name__ == '__main__':
    populate_database()