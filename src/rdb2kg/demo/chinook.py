"""
Chinook demo database builder.

Creates the full 11-table Chinook schema (music store: artists, albums, tracks,
genres, media types, employees, customers, invoices, invoice lines, playlists,
playlist-track associations) as a local SQLite file that the rest of the system
treats as an external database via a connection string.
"""
from pathlib import Path
import sqlalchemy as sa


# ── Table definitions ─────────────────────────────────────────────────────────

def _build_schema(meta: sa.MetaData) -> None:
    sa.Table("Genre", meta,
        sa.Column("GenreId",   sa.Integer, primary_key=True),
        sa.Column("Name",      sa.Text,    nullable=True),
    )
    sa.Table("MediaType", meta,
        sa.Column("MediaTypeId", sa.Integer, primary_key=True),
        sa.Column("Name",        sa.Text,    nullable=True),
    )
    sa.Table("Artist", meta,
        sa.Column("ArtistId", sa.Integer, primary_key=True),
        sa.Column("Name",     sa.Text,    nullable=True),
    )
    sa.Table("Album", meta,
        sa.Column("AlbumId",  sa.Integer, primary_key=True),
        sa.Column("Title",    sa.Text,    nullable=False),
        sa.Column("ArtistId", sa.Integer, sa.ForeignKey("Artist.ArtistId"), nullable=False),
    )
    sa.Table("Track", meta,
        sa.Column("TrackId",      sa.Integer,        primary_key=True),
        sa.Column("Name",         sa.Text,            nullable=False),
        sa.Column("AlbumId",      sa.Integer,         sa.ForeignKey("Album.AlbumId"),     nullable=True),
        sa.Column("MediaTypeId",  sa.Integer,         sa.ForeignKey("MediaType.MediaTypeId"), nullable=False),
        sa.Column("GenreId",      sa.Integer,         sa.ForeignKey("Genre.GenreId"),     nullable=True),
        sa.Column("Composer",     sa.Text,            nullable=True),
        sa.Column("Milliseconds", sa.Integer,         nullable=False),
        sa.Column("Bytes",        sa.Integer,         nullable=True),
        sa.Column("UnitPrice",    sa.Numeric(10, 2),  nullable=False),
    )
    sa.Table("Employee", meta,
        sa.Column("EmployeeId", sa.Integer, primary_key=True),
        sa.Column("LastName",   sa.Text,    nullable=False),
        sa.Column("FirstName",  sa.Text,    nullable=False),
        sa.Column("Title",      sa.Text,    nullable=True),
        sa.Column("ReportsTo",  sa.Integer, sa.ForeignKey("Employee.EmployeeId"), nullable=True),
        sa.Column("BirthDate",  sa.Text,    nullable=True),
        sa.Column("HireDate",   sa.Text,    nullable=True),
        sa.Column("Address",    sa.Text,    nullable=True),
        sa.Column("City",       sa.Text,    nullable=True),
        sa.Column("State",      sa.Text,    nullable=True),
        sa.Column("Country",    sa.Text,    nullable=True),
        sa.Column("PostalCode", sa.Text,    nullable=True),
        sa.Column("Phone",      sa.Text,    nullable=True),
        sa.Column("Fax",        sa.Text,    nullable=True),
        sa.Column("Email",      sa.Text,    nullable=True),
    )
    sa.Table("Customer", meta,
        sa.Column("CustomerId",   sa.Integer, primary_key=True),
        sa.Column("FirstName",    sa.Text,    nullable=False),
        sa.Column("LastName",     sa.Text,    nullable=False),
        sa.Column("Company",      sa.Text,    nullable=True),
        sa.Column("Address",      sa.Text,    nullable=True),
        sa.Column("City",         sa.Text,    nullable=True),
        sa.Column("State",        sa.Text,    nullable=True),
        sa.Column("Country",      sa.Text,    nullable=True),
        sa.Column("PostalCode",   sa.Text,    nullable=True),
        sa.Column("Phone",        sa.Text,    nullable=True),
        sa.Column("Fax",          sa.Text,    nullable=True),
        sa.Column("Email",        sa.Text,    nullable=False),
        sa.Column("SupportRepId", sa.Integer, sa.ForeignKey("Employee.EmployeeId"), nullable=True),
    )
    sa.Table("Invoice", meta,
        sa.Column("InvoiceId",         sa.Integer,        primary_key=True),
        sa.Column("CustomerId",        sa.Integer,        sa.ForeignKey("Customer.CustomerId"), nullable=False),
        sa.Column("InvoiceDate",       sa.Text,           nullable=False),
        sa.Column("BillingAddress",    sa.Text,           nullable=True),
        sa.Column("BillingCity",       sa.Text,           nullable=True),
        sa.Column("BillingState",      sa.Text,           nullable=True),
        sa.Column("BillingCountry",    sa.Text,           nullable=True),
        sa.Column("BillingPostalCode", sa.Text,           nullable=True),
        sa.Column("Total",             sa.Numeric(10, 2), nullable=False),
    )
    sa.Table("InvoiceLine", meta,
        sa.Column("InvoiceLineId", sa.Integer,        primary_key=True),
        sa.Column("InvoiceId",     sa.Integer,        sa.ForeignKey("Invoice.InvoiceId"), nullable=False),
        sa.Column("TrackId",       sa.Integer,        sa.ForeignKey("Track.TrackId"),   nullable=False),
        sa.Column("UnitPrice",     sa.Numeric(10, 2), nullable=False),
        sa.Column("Quantity",      sa.Integer,        nullable=False),
    )
    sa.Table("Playlist", meta,
        sa.Column("PlaylistId", sa.Integer, primary_key=True),
        sa.Column("Name",       sa.Text,    nullable=True),
    )
    sa.Table("PlaylistTrack", meta,
        sa.Column("PlaylistId", sa.Integer, sa.ForeignKey("Playlist.PlaylistId"), nullable=False, primary_key=True),
        sa.Column("TrackId",    sa.Integer, sa.ForeignKey("Track.TrackId"),    nullable=False, primary_key=True),
    )


# ── Seed data ─────────────────────────────────────────────────────────────────

_GENRES = [
    (1,  "Rock"),            (2,  "Jazz"),
    (3,  "Metal"),           (4,  "Alternative & Punk"),
    (5,  "Rock And Roll"),   (6,  "Blues"),
    (7,  "Latin"),           (8,  "Reggae"),
    (9,  "Pop"),             (10, "Soundtrack"),
    (11, "Bossa Nova"),      (12, "Easy Listening"),
    (13, "Heavy Metal"),     (14, "R&B/Soul"),
    (15, "Electronica/Dance"),
]

_MEDIA_TYPES = [
    (1, "MPEG audio file"),
    (2, "Protected AAC audio file"),
    (3, "Protected MPEG-4 video file"),
    (4, "Purchased AAC audio file"),
    (5, "AAC audio file"),
]

_ARTISTS = [
    (1,  "AC/DC"),              (2,  "Accept"),
    (3,  "Aerosmith"),          (4,  "Alanis Morissette"),
    (5,  "Alice In Chains"),    (6,  "Antonio Carlos Jobim"),
    (7,  "Apocalyptica"),       (8,  "Audioslave"),
    (9,  "BackBeat"),           (10, "Billy Cobham"),
    (11, "Black Label Society"),(12, "Black Sabbath"),
    (13, "Body Count"),         (14, "Bruce Dickinson"),
    (15, "Buddy Guy"),
]

_ALBUMS = [
    (1,  "For Those About To Rock We Salute You", 1),
    (2,  "Balls to the Wall",                     2),
    (3,  "Restless and Wild",                     2),
    (4,  "Let There Be Rock",                     1),
    (5,  "Big Ones",                              3),
    (6,  "Jagged Little Pill",                    4),
    (7,  "Facelift",                              5),
    (8,  "Warner 25 Anos",                        6),
    (9,  "Plays Metallica By Four Cellos",        7),
    (10, "Audioslave",                            8),
    (11, "BackBeat Soundtrack",                   9),
    (12, "The Best Of Billy Cobham",              10),
    (13, "Alcohol Fueled Brewtality Live! [Disc 1]", 11),
    (14, "Black Sabbath",                         12),
    (15, "Black Sabbath Vol. 4 (Remaster)",       12),
    (16, "Body Count",                            13),
    (17, "Chemical Wedding",                      14),
    (18, "The Best of Buddy Guy",                 15),
    (19, "Dirt",                                  5),
    (20, "The Symphony No. 9",                    6),
]

# (TrackId, Name, AlbumId, MediaTypeId, GenreId, Composer, Milliseconds, Bytes, UnitPrice)
_TRACKS = [
    # Album 1 - For Those About To Rock (AC/DC)
    (1,  "For Those About To Rock (We Salute You)", 1,  1, 1,  "Angus Young, Malcolm Young, Brian Johnson", 343719, 11170334, 0.99),
    (2,  "Put The Finger On You",                   1,  1, 1,  "Angus Young, Malcolm Young, Brian Johnson", 205662,  6713451, 0.99),
    (3,  "Let's Get It Up",                         1,  1, 1,  "Angus Young, Malcolm Young, Brian Johnson", 233926,  7636561, 0.99),
    (4,  "Inject The Venom",                        1,  1, 1,  "Angus Young, Malcolm Young, Brian Johnson", 210834,  6852860, 0.99),
    (5,  "Snowballed",                              1,  1, 1,  "Angus Young, Malcolm Young, Brian Johnson", 203102,  6599424, 0.99),
    # Album 2 - Balls to the Wall (Accept)
    (6,  "Balls to the Wall",                       2,  2, 3,  "U. Dirkschneider & W. Hoffmann",           342562, 10926123, 0.99),
    # Album 3 - Restless and Wild (Accept)
    (7,  "Fast As a Shark",                         3,  2, 3,  "F. Baltes, S. Kaufman, U. Dirkschneider",  230619,  3990994, 0.99),
    (8,  "Restless and Wild",                       3,  2, 3,  "F. Baltes, R.A. Smith-Diesel",             252051,  4331779, 0.99),
    (9,  "Princess of the Dawn",                    3,  2, 3,  "Deaffy & R.A. Smith-Diesel",               375418,  6290521, 0.99),
    # Album 4 - Let There Be Rock (AC/DC)
    (10, "Go Down",                                 4,  1, 1,  "AC/DC",                                    331180, 10847611, 0.99),
    (11, "Dog Eat Dog",                             4,  1, 1,  "AC/DC",                                    215196,  7032162, 0.99),
    (12, "Let There Be Rock",                       4,  1, 1,  "AC/DC",                                    366654, 12021261, 0.99),
    (13, "Bad Boy Boogie",                          4,  1, 1,  "AC/DC",                                    267728,  8776440, 0.99),
    # Album 5 - Big Ones (Aerosmith)
    (14, "Walk On Water",                           5,  1, 1,  "Steven Tyler, Joe Perry",                  295680,  9719579, 0.99),
    (15, "Love In An Elevator",                     5,  1, 1,  "Steven Tyler, Joe Perry",                  321828, 10552051, 0.99),
    (16, "Rag Doll",                                5,  1, 1,  "Steven Tyler, Joe Perry, Brad Whitford",   222946,  7322257, 0.99),
    (17, "What It Takes",                           5,  1, 1,  "Steven Tyler, Joe Perry",                  310622, 10144791, 0.99),
    # Album 6 - Jagged Little Pill (Alanis Morissette)
    (18, "All I Really Want",                       6,  1, 4,  "Alanis Morissette & Glen Ballard",         284891,  9375567, 0.99),
    (19, "You Oughta Know",                         6,  1, 4,  "Alanis Morissette & Glen Ballard",         249234,  8196999, 0.99),
    (20, "Perfect",                                 6,  1, 4,  "Alanis Morissette & Glen Ballard",         188133,  6145404, 0.99),
    (21, "Hand In My Pocket",                       6,  1, 4,  "Alanis Morissette & Glen Ballard",         221570,  7224246, 0.99),
    (22, "Right Through You",                       6,  1, 4,  "Alanis Morissette & Glen Ballard",         176117,  5793082, 0.99),
    # Album 7 - Facelift (Alice In Chains)
    (23, "We Die Young",                            7,  1, 1,  "Jerry Cantrell",                           152084,  4925362, 0.99),
    (24, "Man In The Box",                          7,  1, 1,  "Jerry Cantrell, Layne Staley",             286641,  9310272, 0.99),
    (25, "Sea Of Sorrow",                           7,  1, 1,  "Jerry Cantrell",                           374543, 12222206, 0.99),
    (26, "Bleed The Freak",                         7,  1, 1,  "Jerry Cantrell",                           241946,  7828530, 0.99),
    # Album 9 - Plays Metallica By Four Cellos (Apocalyptica)
    (27, "Enter Sandman",                           9,  1, 3,  "Apocalyptica",                             221701,  7286305, 0.99),
    (28, "Master Of Puppets",                       9,  1, 3,  "Apocalyptica",                             436453, 14357428, 0.99),
    (29, "Harvested",                               9,  1, 3,  "Apocalyptica",                             374319, 12224815, 0.99),
    # Album 10 - Audioslave
    (30, "Like a Stone",                            10, 1, 1,  "Audioslave",                               294034,  9609832, 0.99),
    (31, "Show Me How to Live",                     10, 1, 1,  "Audioslave",                               256946,  8426954, 0.99),
    (32, "Cochise",                                 10, 1, 1,  "Audioslave",                               222686,  7304570, 0.99),
    (33, "Spoonman",                                10, 1, 1,  "Audioslave",                               248573,  8089559, 0.99),
    # Album 14 - Black Sabbath
    (34, "Black Sabbath",                           14, 1, 3,  "Tony Iommi, Bill Ward, Geezer Butler, Ozzy Osbourne", 382066, 12440200, 0.99),
    (35, "The Wizard",                              14, 1, 3,  "Tony Iommi, Bill Ward, Geezer Butler, Ozzy Osbourne", 264829,  8646061, 0.99),
    (36, "Behind The Wall Of Sleep",                14, 1, 3,  "Tony Iommi, Bill Ward, Geezer Butler, Ozzy Osbourne", 217573,  7089903, 0.99),
    # Album 15 - Black Sabbath Vol 4
    (37, "Wheels Of Confusion / The Straightener",  15, 1, 3,  "Tony Iommi, Bill Ward, Geezer Butler, Ozzy Osbourne", 494524, 16065830, 0.99),
    (38, "Tomorrow's Dream",                        15, 1, 3,  "Tony Iommi, Bill Ward, Geezer Butler, Ozzy Osbourne", 192496,  6217450, 0.99),
    (39, "Changes",                                 15, 1, 3,  "Tony Iommi, Bill Ward, Geezer Butler, Ozzy Osbourne", 286719,  9244581, 0.99),
    # Album 17 - Chemical Wedding (Bruce Dickinson)
    (40, "King In Crimson",                         17, 1, 3,  "Bruce Dickinson",                          356471, 11622020, 0.99),
    (41, "Chemical Wedding",                        17, 1, 3,  "Bruce Dickinson",                          233150,  7608182, 0.99),
    # Album 19 - Dirt (Alice In Chains)
    (42, "Them Bones",                              19, 1, 1,  "Jerry Cantrell",                           150748,  4938407, 0.99),
    (43, "Dam That River",                          19, 1, 1,  "Jerry Cantrell",                           232523,  7607734, 0.99),
    (44, "Rain When I Die",                         19, 1, 1,  "Jerry Cantrell, Layne Staley",             344228, 11213816, 0.99),
    (45, "Down In A Hole",                          19, 1, 1,  "Jerry Cantrell",                           330332, 10813386, 0.99),
    # Album 16 - Body Count
    (46, "Cop Killer",                              16, 1, 1,  "Ice-T & Ernie C",                          230374,  7585003, 0.99),
    (47, "Body Count",                              16, 1, 1,  "Ice-T & Ernie C",                          223216,  7324237, 0.99),
    # Album 8 - Warner 25 Anos (Jobim)
    (48, "Desafinado",                              8,  1, 11, "Antonio Carlos Jobim",                     185338,  5990473, 0.99),
    (49, "Garota De Ipanema",                       8,  1, 11, "Vinicius De Moraes & Antonio Carlos Jobim",285048,  9348428, 0.99),
    (50, "Sabia",                                   8,  1, 11, "Antonio Carlos Jobim",                     269440,  8844445, 0.99),
]

_EMPLOYEES = [
    # (EmployeeId, LastName, FirstName, Title, ReportsTo, BirthDate, HireDate, Address, City, State, Country, PostalCode, Phone, Fax, Email)
    (1, "Adams",    "Andrew",  "General Manager",          None, "1962-02-18", "2002-08-14", "11120 Jasper Ave NW", "Edmonton",   "AB", "Canada", "T5K 2N1", "+1 (780) 428-9482", "+1 (780) 428-3457", "andrew@chinookcorp.com"),
    (2, "Edwards",  "Nancy",   "Sales Manager",            1,    "1958-12-08", "2002-05-01", "825 8 Ave SW",        "Calgary",    "AB", "Canada", "T2P 2T3", "+1 (403) 262-3443", "+1 (403) 262-3322", "nancy@chinookcorp.com"),
    (3, "Peacock",  "Jane",    "Sales Support Agent",      2,    "1973-08-29", "2002-04-01", "1111 6 Ave SW",       "Calgary",    "AB", "Canada", "T2P 5M5", "+1 (403) 262-3443", "+1 (403) 262-6712", "jane@chinookcorp.com"),
    (4, "Park",     "Margaret","Sales Support Agent",      2,    "1947-09-19", "2003-05-03", "683 10 Street SW",    "Calgary",    "AB", "Canada", "T2P 5G3", "+1 (403) 263-4423", "+1 (403) 263-4289", "margaret@chinookcorp.com"),
    (5, "Johnson",  "Steve",   "Sales Support Agent",      2,    "1965-03-03", "2003-10-17", "7727B 41 Ave",        "Calgary",    "AB", "Canada", "T3B 1Y7", "1 (780) 836-9987",  "1 (780) 836-9543",  "steve@chinookcorp.com"),
    (6, "Mitchell", "Michael", "IT Manager",               1,    "1973-07-01", "2003-10-17", "5827 Bowness Road NW","Calgary",    "AB", "Canada", "T3B 0C5", "+1 (403) 246-9887", "+1 (403) 246-9899", "michael@chinookcorp.com"),
    (7, "King",     "Robert",  "IT Staff",                 6,    "1970-05-29", "2004-01-02", "590 Columbia Boulevard W", "Lethbridge", "AB", "Canada", "T1K 5N8", "+1 (403) 456-9986", "+1 (403) 456-8485", "robert@chinookcorp.com"),
    (8, "Callahan", "Laura",   "IT Staff",                 6,    "1968-01-09", "2004-03-04", "923 7 ST NW",         "Lethbridge", "AB", "Canada", "T1H 1Y8", "+1 (403) 467-3351", "+1 (403) 467-8772", "laura@chinookcorp.com"),
]

_CUSTOMERS = [
    # (CustomerId, FirstName, LastName, Company, Address, City, State, Country, PostalCode, Phone, Fax, Email, SupportRepId)
    (1,  "Luís",    "Goncalves", "Embraer - Empresa Brasileira de Aeronáutica S.A.", "Av. Brigadeiro Faria Lima, 2170", "São José dos Campos", "SP", "Brazil",  "12227-000", "+55 (12) 3923-5555", "+55 (12) 3923-5566", "luisg@embraer.com.br", 3),
    (2,  "Leonie",  "Köhler",    None,                     "Theodor-Heuss-Straße 34", "Stuttgart",    None,   "Germany",        "70174",      "+49 0711 2842222", None,               "leonekohler@surfeu.de", 5),
    (3,  "François","Tremblay",  None,                     "1498 rue Bélanger",       "Montréal",     "QC",   "Canada",         "H2G 1A7",    "+1 (514) 721-4711", None,              "ftremblay@gmail.com",  3),
    (4,  "Bjørn",   "Hansen",    None,                     "Ullevålsveien 14",        "Oslo",         None,   "Norway",         "0171",       "+47 22 44 22 22",   None,              "bjorn.hansen@yahoo.no", 4),
    (5,  "Frantisek","Wichterlova","JetBrains s.r.o.",     "Klanova 9/506",           "Prague",       None,   "Czech Republic", "14700",      "+420 2 4172 5555",  "+420 2 4172 5555","frantisekw@jetbrains.com", 4),
    (6,  "Helena",  "Holý",      None,                     "Rilská 3174/6",           "Prague",       None,   "Czech Republic", "14300",      "+420 2 4177 0449",  None,              "hholy@gmail.com",      5),
    (7,  "Astrid",  "Gruber",    None,                     "Rotenturmstraße 4, 1010 Innere Stadt", "Vienne", None, "Austria",   "1010",       "+43 01 5134505",    None,              "astrid.gruber@apple.at", 5),
    (8,  "Daan",    "Peeters",   None,                     "Grétrystraat 63",         "Brussels",     None,   "Belgium",        "1000",       "+32 02 219 03 03",  None,              "daan_peeters@apple.be", 4),
    (9,  "Kara",    "Nielsen",   None,                     "Sønder Boulevard 51",     "Copenhagen",   None,   "Denmark",        "1720",       "+453 3331 9991",    None,              "kara.nielsen@jubii.dk", 4),
    (10, "Eduardo", "Martins",   "Woodstock Discos",       "Rua Dr. Falcão Filho, 155","São Paulo",   "SP",   "Brazil",         "01007-010",  "+55 (11) 3033-5446","+55 (11) 3033-4564","eduardo@woodstock.com.br", 4),
]

_INVOICES = [
    # (InvoiceId, CustomerId, InvoiceDate, BillingAddress, BillingCity, BillingState, BillingCountry, BillingPostalCode, Total)
    (1,  2,  "2021-01-01", "Theodor-Heuss-Straße 34", "Stuttgart",    None,  "Germany",        "70174",    1.98),
    (2,  4,  "2021-01-02", "Ullevålsveien 14",         "Oslo",         None,  "Norway",         "0171",     3.96),
    (3,  8,  "2021-01-03", "Grétrystraat 63",          "Brussels",     None,  "Belgium",        "1000",     5.94),
    (4,  14, "2021-02-11", "8210 111 ST NW",           "Edmonton",     "AB",  "Canada",         "T6G 2C7",  8.91),
    (5,  23, "2021-02-11", "69 Salem Street",          "Boston",       "MA",  "USA",            "2113",    13.86),
    (6,  1,  "2021-03-04", "Av. Brigadeiro Faria Lima","São José dos Campos","SP","Brazil",     "12227-000",0.99),
    (7,  3,  "2021-04-05", "1498 rue Bélanger",        "Montréal",     "QC",  "Canada",         "H2G 1A7",  1.98),
    (8,  5,  "2021-04-05", "Klanova 9/506",            "Prague",       None,  "Czech Republic", "14700",    1.98),
    (9,  7,  "2021-04-09", "Rotenturmstraße 4, 1010",  "Vienne",       None,  "Austria",        "1010",     3.96),
    (10, 9,  "2021-05-11", "Sønder Boulevard 51",      "Copenhagen",   None,  "Denmark",        "1720",     5.94),
    (11, 10, "2021-06-11", "Rua Dr. Falcão Filho, 155","São Paulo",    "SP",  "Brazil",         "01007-010",8.91),
    (12, 6,  "2021-07-11", "Rilská 3174/6",            "Prague",       None,  "Czech Republic", "14300",    0.99),
    (13, 1,  "2021-09-01", "Av. Brigadeiro Faria Lima","São José dos Campos","SP","Brazil",     "12227-000",1.98),
    (14, 2,  "2021-11-01", "Theodor-Heuss-Straße 34",  "Stuttgart",    None,  "Germany",        "70174",    3.96),
    (15, 3,  "2022-01-16", "1498 rue Bélanger",        "Montréal",     "QC",  "Canada",         "H2G 1A7",  5.94),
]

_INVOICE_LINES = [
    # (InvoiceLineId, InvoiceId, TrackId, UnitPrice, Quantity)
    (1,  1,  2,  0.99, 1),
    (2,  1,  4,  0.99, 1),
    (3,  2,  6,  0.99, 1),
    (4,  2,  8,  0.99, 1),
    (5,  2,  10, 0.99, 1),
    (6,  2,  12, 0.99, 1),
    (7,  3,  16, 0.99, 1),
    (8,  3,  20, 0.99, 1),
    (9,  3,  24, 0.99, 1),
    (10, 3,  28, 0.99, 1),
    (11, 3,  30, 0.99, 1),
    (12, 3,  32, 0.99, 1),
    (13, 4,  34, 0.99, 1),
    (14, 4,  35, 0.99, 1),
    (15, 4,  36, 0.99, 1),
    (16, 4,  37, 0.99, 1),
    (17, 4,  38, 0.99, 1),
    (18, 4,  39, 0.99, 1),
    (19, 4,  40, 0.99, 1),
    (20, 4,  41, 0.99, 1),
    (21, 4,  42, 0.99, 1),
    (22, 5,  1,  0.99, 1),
    (23, 5,  3,  0.99, 1),
    (24, 5,  7,  0.99, 1),
    (25, 5,  9,  0.99, 1),
    (26, 5,  11, 0.99, 1),
    (27, 5,  13, 0.99, 1),
    (28, 5,  15, 0.99, 1),
    (29, 5,  17, 0.99, 1),
    (30, 5,  19, 0.99, 1),
    (31, 5,  21, 0.99, 1),
    (32, 5,  23, 0.99, 1),
    (33, 5,  25, 0.99, 1),
    (34, 5,  27, 0.99, 1),
    (35, 6,  43, 0.99, 1),
    (36, 7,  44, 0.99, 1),
    (37, 7,  45, 0.99, 1),
    (38, 8,  46, 0.99, 1),
    (39, 8,  47, 0.99, 1),
    (40, 9,  48, 0.99, 1),
    (41, 9,  49, 0.99, 1),
    (42, 9,  50, 0.99, 1),
    (43, 9,  5,  0.99, 1),
    (44, 10, 14, 0.99, 1),
    (45, 10, 18, 0.99, 1),
    (46, 10, 22, 0.99, 1),
    (47, 10, 26, 0.99, 1),
    (48, 10, 29, 0.99, 1),
    (49, 10, 31, 0.99, 1),
    (50, 11, 33, 0.99, 1),
]

_PLAYLISTS = [
    (1,  "Music"),
    (2,  "Movies"),
    (3,  "TV Shows"),
    (4,  "Audiobooks"),
    (5,  "90s Music"),
    (8,  "Music Videos"),
    (9,  "Classic Rock"),
    (10, "Classical"),
    (11, "Heavy Metal"),
    (12, "Classical 101 - Deep Cuts"),
]

_PLAYLIST_TRACKS = [
    # Playlist 1 (Music) - broad sample
    (1, 1), (1, 2), (1, 3), (1, 6), (1, 10), (1, 14), (1, 18), (1, 23),
    (1, 27), (1, 30), (1, 34), (1, 42), (1, 48),
    # Playlist 5 (90s Music)
    (5, 18), (5, 19), (5, 20), (5, 21), (5, 22),  # Alanis
    (5, 23), (5, 24), (5, 25),                     # Alice In Chains Facelift
    (5, 42), (5, 43),                              # Dirt
    # Playlist 9 (Classic Rock)
    (9, 1), (9, 2), (9, 3), (9, 4), (9, 5),       # AC/DC
    (9, 10), (9, 11), (9, 12), (9, 13),            # Let There Be Rock
    # Playlist 11 (Heavy Metal)
    (11, 6), (11, 7), (11, 8), (11, 9),           # Accept
    (11, 27), (11, 28), (11, 29),                  # Apocalyptica
    (11, 34), (11, 35), (11, 36),                  # Black Sabbath
]


# ── Database creation ─────────────────────────────────────────────────────────

def create_chinook_db(path: Path) -> None:
    """Create (or recreate) the Chinook SQLite database at *path*."""
    engine = sa.create_engine(f"sqlite:///{path}")
    meta = sa.MetaData()
    _build_schema(meta)
    meta.create_all(engine)

    tables = meta.tables
    with engine.begin() as conn:
        conn.execute(tables["Genre"].insert(),        [{"GenreId": g, "Name": n} for g, n in _GENRES])
        conn.execute(tables["MediaType"].insert(),     [{"MediaTypeId": m, "Name": n} for m, n in _MEDIA_TYPES])
        conn.execute(tables["Artist"].insert(),        [{"ArtistId": a, "Name": n} for a, n in _ARTISTS])
        conn.execute(tables["Album"].insert(),         [{"AlbumId": al, "Title": t, "ArtistId": ar} for al, t, ar in _ALBUMS])
        conn.execute(tables["Track"].insert(),         [
            {"TrackId": tid, "Name": n, "AlbumId": alb, "MediaTypeId": mt,
             "GenreId": g, "Composer": comp, "Milliseconds": ms, "Bytes": b, "UnitPrice": up}
            for tid, n, alb, mt, g, comp, ms, b, up in _TRACKS
        ])
        conn.execute(tables["Employee"].insert(),      [
            {"EmployeeId": eid, "LastName": ln, "FirstName": fn, "Title": ti,
             "ReportsTo": rt, "BirthDate": bd, "HireDate": hd, "Address": addr,
             "City": city, "State": state, "Country": country, "PostalCode": pc,
             "Phone": ph, "Fax": fax, "Email": em}
            for eid, ln, fn, ti, rt, bd, hd, addr, city, state, country, pc, ph, fax, em in _EMPLOYEES
        ])
        conn.execute(tables["Customer"].insert(),      [
            {"CustomerId": cid, "FirstName": fn, "LastName": ln, "Company": co,
             "Address": addr, "City": city, "State": state, "Country": country,
             "PostalCode": pc, "Phone": ph, "Fax": fax, "Email": em, "SupportRepId": sr}
            for cid, fn, ln, co, addr, city, state, country, pc, ph, fax, em, sr in _CUSTOMERS
        ])
        conn.execute(tables["Invoice"].insert(),       [
            {"InvoiceId": iid, "CustomerId": cid, "InvoiceDate": dt,
             "BillingAddress": ba, "BillingCity": bc, "BillingState": bs,
             "BillingCountry": bco, "BillingPostalCode": bpc, "Total": tot}
            for iid, cid, dt, ba, bc, bs, bco, bpc, tot in _INVOICES
        ])
        conn.execute(tables["InvoiceLine"].insert(),   [
            {"InvoiceLineId": lid, "InvoiceId": iid, "TrackId": tid,
             "UnitPrice": up, "Quantity": qty}
            for lid, iid, tid, up, qty in _INVOICE_LINES
        ])
        conn.execute(tables["Playlist"].insert(),      [{"PlaylistId": pid, "Name": n} for pid, n in _PLAYLISTS])
        conn.execute(tables["PlaylistTrack"].insert(), [{"PlaylistId": pid, "TrackId": tid} for pid, tid in _PLAYLIST_TRACKS])

    engine.dispose()
