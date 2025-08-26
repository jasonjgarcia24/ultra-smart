#!/usr/bin/env python3

import re
from database import UltraSmartDatabase

def parse_time(time_str):
    """Parse time string like '58:47:18' to hours as float."""
    if not time_str or time_str == '0':
        return None
    
    parts = time_str.split(':')
    if len(parts) == 3:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])
        return hours + minutes/60 + seconds/3600
    return None

def import_cocodona_2025_results():
    """Import the actual 2025 Cocodona 250 results."""
    db = UltraSmartDatabase()
    
    # Clear existing data and recreate the race
    race_id = db.add_race(
        name="Cocodona 250",
        year=2025,
        date="2025-05-05",
        location="Black Canyon City to Flagstaff, AZ",
        distance_miles=256,
        elevation_gain_feet=40000,
        elevation_loss_feet=35000,
        time_limit_hours=125,
        course_description="Point-to-point course through the Sonoran Desert and high country of Arizona",
        ultrasignup_id="115785"
    )
    
    # Raw results data (as provided by user)
    results_data = """
results	1	Dan	Green	Huntington	WV	28	M	1	58:47:18	94.27
results	2	Ryan	Sandes	Cape Town		43	M	2	61:21:04	94.1
results	3	Edher	Ramirez	Las Vegas	NV	39	M	3	63:10:13	81.74
results	4	Rachel	Entrekin	Conifer	CO	33	F	1	63:50:55	93.19
results	5	Haroldas	Subertas	Haines	AK	33	M	4	65:28:53	93.34
results	6	Finn	Melanson	Salt Lake City	UT	33	M	5	66:29:40	85.45
results	7	Dj	Fox	Durango	CO	32	M	6	69:28:01	84.18
results	8	Cody	Poskin	Cedar Hill	MO	23	M	7	71:11:53	84.66
results	9	Michael	McKnight	Smithfield	UT	35	M	8	71:56:52	83.92
results	10	Jeff	Garmire	Bozeman	MT	34	M	9	77:37:32	89.27
results	11	Chad	Salyer	Fort Worth	TX	38	M	10	78:51:04	82.96
results	12	Michael	Puett	Boise	ID	34	M	11	79:16:50	86.86
results	13	Lindsey	Dwyer	Larkspur	CA	33	F	2	79:35:28	93.15
results	14	Aaron	Young	Oakford		38	M	12	80:08:03	69.62
results	15	Sarah	Ostaszewski	Durango	CO	33	F	3	80:25:31	86.6
results	16	Kevin	Goldberg	Westminster	CO	36	M	13	81:01:18	71.44
results	17	Brian	Janezic	Tucson	AZ	38	M	14	81:51:42	71.83
results	18	Cameron	Hanes	Springfield	OR	57	M	15	84:33:37	81.89
results	18	Ryan	Kunz	Tallahassee	FL	42	M	15	84:33:37	80.27
results	20	Dante	Dugan	Alameda	CA	37	M	17	84:42:30	69.76
results	21	Shelby	Farrell	Colorado Springs	CO	34	F	4	85:26:23	81.05
results	22	Melissa	Browne	Spokane	WA	41	F	5	85:45:23	77.1
results	23	Nathan	Hannemann	Parker	CO	39	M	18	85:47:36	68.92
results	24	Katherine	Edwards Anderson	McGaheysville	VA	25	F	6	85:52:20	85.28
results	25	Daniel	Bishop	Canonsburg	PA	37	M	19	86:25:21	70.43
results	26	Adam	Williams	Pullman	WA	38	M	20	88:01:24	70.86
results	27	Niklas	Steinbrunner	Springfield	OH	28	M	21	88:05:07	77.83
results	28	Deric	Anthony	San Marcos	CA	28	M	22	88:35:48	56.44
results	29	Kyle	Cameron	Flagstaff	AZ	35	M	23	89:00:40	79.08
results	30	Eli	Wehbe	Los Angeles	CA	37	M	24	89:16:19	68.63
results	31	Jennie	Chisholm	Salem	NH	49	F	7	89:19:58	72.31
results	32	Luke	Smith	Ashland	OR	38	M	25	90:08:52	72.65
results	33	Chris	Metaxas	Conestogo	ON	39	M	26	90:21:33	64.77
results	34	Jose	Sosa	Chula Vista	CA	43	M	27	90:36:31	72.72
results	35	Rolando	Mendoza	Ontario	CA	35	M	28	90:37:55	71.26
results	36	Kyle	Colavito	Flagstaff	AZ	44	M	29	90:50:46	79.83
results	37	Joel	Thurston	Peoria	AZ	47	M	30	93:12:25	71.37
results	38	Michael	Greer	Peoria	AZ	42	M	31	93:25:04	84.8
results	39	Anthony	Seifert	San Diego	CA	33	M	32	93:58:36	85.74
results	40	Coree	Woltering	Jackman	ME	35	M	33	94:04:52	85.91
results	41	Carrie	Setian	Anchorage	AK	45	F	8	94:24:26	75.92
results	42	Elliott	Waldock	Parshall	ND	32	M	34	95:52:49	63.17
results	43	Garrett	Nelson	Black Earth	WI	32	M	35	97:33:34	82.18
results	44	Kevin	Russ	Portland	OR	42	M	36	98:00:39	76.86
results	45	James	Nalley	Prescott Valley	AZ	56	M	37	98:04:42	81.63
results	46	Emily	Flinn	Lemont Furnace	PA	40	F	9	98:37:28	79.26
results	47	Brock	Everhart	Canal Winchester	OH	43	M	38	98:56:26	78.54
results	48	Michael	Kershen	Denver	CO	43	M	39	99:25:49	78.42
results	49	Simon	Guerard	Carlsbad	CA	39	M	40	99:31:50	66.9
results	50	Brenyn	St.Vrain	Wichita	KS	23	M	41	99:41:33	77.12
results	51	Alexa	Hasman	Portland	OR	41	F	10	99:45:05	71.65
results	52	Wyatt	Barrett	Yosemite Valley	CA	27	M	42	99:50:00	81.81
results	53	Dmytro	Sokolovskyy	Moorpark	CA	36	M	43	99:56:40	65.73
results	54	Stormy	Hild	Athens	IL	33	M	44	99:59:38	73.87
results	55	Jason	Midlock	Joliet	IL	40	M	45	100:01:43	76.98
results	56	Maia	Detmer	Las Vegas	NV	43	F	11	101:06:53	85.56
results	57	Caleb	Baybayan	Vancouver	WA	31	M	46	101:11:59	81.87
results	58	Rachel	Buzzard	Flagstaff	AZ	39	F	12	101:18:03	86.94
results	59	Kevin	Bott	Scottsdale	AZ	42	M	47	101:30:43	56.41
results	60	Josh	Frewin	Camp Verde	AZ	33	M	48	101:41:30	67.64
results	61	Chris	Haas	Hesperia	CA	38	M	49	101:53:57	57.54
results	62	Allison	Powell	Bozeman	MT	33	F	13	102:06:04	86.37
results	63	Jose	Montellano	Riverside	CA	38	M	50	103:05:20	72.97
results	64	Di	Wu	Shulan		41	M	51	103:15:02	67.57
results	65	Sam	Fulbright	Knoxville	TN	35	M	52	103:34:17	75.78
results	66	Justin	Faul	Warrenton	VA	44	M	53	103:43:29	80.22
results	67	Pete	Griggs	Delaware	OH	52	M	54	104:09:33	67.28
results	68	Bryce	Burchi	Phoenix	AZ	28	M	55	104:29:38	73.41
results	69	Ryan	Bailey	Wittmann	AZ	28	M	56	104:58:41	63.98
results	70	Rob	Espenel	Eagle	CO	49	M	57	105:38:52	69.08
results	71	Deb	Huntzinger	Flagstaff	AZ	49	F	14	106:03:53	74.07
results	72	Kalie	Demerjian	Savannah	GA	28	F	15	106:31:28	84.35
results	73	Logan	Moses	Durham	NC	28	M	58	106:32:15	72.03
results	74	Carmen	Cramer	Brooklyn	NY	42	F	16	106:33:20	79.58
results	75	Brian	Schwartz	Brooklyn	NY	48	M	59	106:33:21	67.42
results	76	Andrew	Glaze	Redlands	CA	47	M	60	106:56:53	70.31
results	77	Matthew	Markowycz	Phoenix	AZ	44	M	61	107:00:07	64.39
results	78	Mason	Newberry	Atlanta	GA	27	M	62	107:53:23	83.88
results	79	Kevin	Fleeger	Ponte Vedra	FL	65	M	63	108:09:06	70.11
results	80	Hunter	Birt	Keller	TX	26	M	64	108:17:34	66.57
results	81	Ben	Lehman	Patagonia	AZ	33	M	65	108:19:17	78.38
results	82	Mitsuo	Moriya	Oyama Shi		46	M	66	108:35:26	59.26
results	83	Pete	Mehok	Georgetown	TX	46	M	67	108:35:53	77.77
results	84	John	Henderson	Cartersville	GA	44	M	68	108:40:18	65.77
results	85	Jack	Pennington	Huntington	WV	23	M	69	109:00:26	66.29
results	86	Daniel	Lockhart	Durham	NC	38	M	70	109:08:01	79.34
results	87	Katie	O'Connor	Chicago	IL	47	F	17	109:20:23	71.37
results	88	Kabuki	Snyder	Venice	CA	51	F	18	109:26:09	66.22
results	89	Jordan	Copenhafer	Gilbertsville	PA	40	M	71	109:31:09	65.71
results	90	Joshua	Rogers	Signal Mountain	TN	45	M	72	109:35:48	76.32
results	91	David	Brownrigg	Flushing	MI	41	M	73	109:40:16	67.4
results	92	Anthony	Certa	Toms River	NJ	41	M	74	109:53:44	71.1
results	93	Aaron	Fleisher	Las Vegas	NV	42	M	75	109:55:56	60.8
results	94	Junior	Fregoso	Gilroy	CA	46	M	76	109:57:45	64.19
results	95	Tyler	Barrett	Kimberly	ID	41	M	77	110:30:34	70.85
results	96	Tobias	Steele	Brisbane		30	M	78	110:54:03	60.94
results	97	Hesham	Abdunnasir	Santa Monica	CA	42	M	79	111:17:28	52.82
results	98	Catherine	Lynch	Spring	TX	35	F	19	111:26:49	63.38
results	99	Anna	Nosek	West Jordan	UT	36	F	20	111:45:35	79.62
results	100	Murray	Holland	Cape Town		40	M	80	111:58:58	52.5
results	101	Ashley	Durstine	Surprise	AZ	43	F	21	112:16:16	80.96
results	102	Des'arae	Stephens	Flagstaff	AZ	31	F	22	112:40:28	62.72
results	103	Gracie	Shoell	South Jordan	UT	24	F	23	112:53:16	69.1
results	104	Sarah	Wallace	Pittsburgh	PA	43	F	24	112:54:57	81.27
results	105	Martin	Roldan	Val-David	QC	52	M	81	112:58:35	58.63
results	106	Christopher	Bord	Wailuku	HI	32	M	82	113:02:56	56.28
results	107	Jackie	Fritsch	Ouray	CO	41	F	25	113:05:22	75.2
results	108	Katelyn	Johnson	Fort Collins	CO	34	F	26	113:05:23	73.05
results	109	Tracy	Denbleyker	Fennville	MI	54	F	27	113:09:41	79.65
results	110	Chase	Martinig	Port Moody	BC	41	M	83	113:25:33	55.04
results	111	Randi	Zuckerberg	Armonk	NY	43	F	28	113:29:45	80.13
results	112	Wes	Plate	Everett	WA	51	M	84	113:31:16	68.91
results	113	Brandan	Bowie	Gallup	NM	33	M	85	113:38:37	62.92
results	114	Eric	Salgado	Anaheim	CA	37	M	86	113:43:38	67.9
results	115	David	D'Haene	Laingsburg	MI	58	M	87	113:49:35	68.55
results	116	Calvin	Duvall	Saint Joseph	MO	25	M	88	114:00:34	80.12
results	117	Ian	Douglas	Mission Viejo	CA	47	M	89	114:02:18	47.81
results	118	Kate	Tsai	Breckenridge	CO	49	F	29	114:19:24	67.11
results	119	Erin	Keilman	Fort Collins	CO	45	F	30	114:24:47	65.98
results	120	Mila	Opalenik	Mount Shasta	CA	22	F	31	114:26:11	72.89
results	121	Szilvia	Lubics	Nagykanizsa		50	F	32	114:26:50	81.95
results	122	Kimber	Snow	Raymond	AB	33	F	33	114:43:47	78.25
results	123	Peter	Brown	Carmichael	CA	40	M	90	114:47:14	55.33
results	124	Kyle	Sharow	Tallahassee	FL	38	M	91	114:52:56	70.6
results	125	Joe	Schrum	Hereford	AZ	56	M	92	114:56:49	61.81
results	126	Jenny	Dolak	Sierra Vista	AZ	59	F	34	114:57:50	71.77
results	127	Jackson	Wolf	Flagstaff	AZ	45	M	93	115:10:10	94.22
results	128	Jonathan	Dawson	Culver City	CA	36	M	94	115:10:35	68.95
results	129	Colin	O'Brien	Duvall	WA	40	M	95	115:19:03	75.92
results	130	Bryant	Shook	Yucaipa	CA	35	M	96	115:22:30	67.12
results	131	Nora	O'Malley	Longmont	CO	36	F	35	115:25:11	77.63
results	132	Michael	Reardon	Lewisville	NC	44	M	97	115:30:19	57.62
results	133	Caitlin	Walters	Brevard	NC	32	F	36	115:31:08	71.08
results	134	Josh	Nelson	Chester	VA	40	M	98	115:34:37	71.16
results	135	Nick	Richardson	Las Cruces	NM	51	M	99	115:49:07	64.28
results	136	Michael	Whittemore	Concord	NH	37	M	100	115:56:45	70.24
results	137	Matthew	Marwick	North Vancouver	BC	31	M	101	115:57:34	54.63
results	138	John	Music	Las Vegas	NV	40	M	102	116:40:13	66.98
results	139	Jared	Harding	Gilbert	AZ	45	M	103	116:51:17	53.14
results	140	Andy	Jones-Wilkins	Phoenix	AZ	57	M	104	116:59:22	80.07
results	141	Renata	Skersyte	Los Alamos	NM	44	F	37	117:34:18	77.55
results	142	Salvador	Castillo	Zamora		38	M	105	117:34:53	56.04
results	143	Peter	Von Hacht	Perth		39	M	106	117:48:02	49.9
results	144	Erick	Passmore	Howard	CO	30	M	107	117:50:54	59.13
results	145	Chad	Endsley	Lima	OH	39	M	108	118:06:48	72.89
results	146	Andrea	Moore	Flagstaff	AZ	47	F	38	118:21:32	68.74
results	147	Kyla	Maher	Bozeman	MT	40	F	39	118:29:43	85.08
results	148	Trey	Hicks	Marietta	GA	54	M	109	118:30:56	62.9
results	149	Alex	Offer	Tucson	AZ	36	M	110	118:41:18	47.74
results	150	Thomas	Polen	Chandler	AZ	51	M	111	118:44:55	60.48
results	151	Tony	Lievanos	Tustin	CA	51	M	112	118:46:40	59.08
results	152	Becca	Skolnick	Fairport	NY	24	F	40	118:49:10	71.92
results	153	Tanessa	Cline	Arvada	CO	44	F	41	118:56:58	65.82
results	154	Shad	Birkholz	Bozeman	MT	48	M	113	119:05:39	59.9
results	155	Joseph	Haist	Charlestown	IN	48	M	114	119:17:15	50.25
results	156	Tug	Boren	Weatherford	TX	17	M	115	120:10:50	63.32
results	157	Jeremy	Hedges	Salida	CO	50	M	116	120:16:20	63.99
results	158	Michelle	Goldberg	Meadowbrook	PA	50	F	42	120:21:47	79.66
results	159	Gina	Bolton	Longview	TX	45	F	43	120:46:58	71.98
results	160	Alex	Ochoa	Tucson	AZ	37	M	117	120:48:52	63.07
results	161	David	Veronesi	Salem	CT	58	M	118	121:02:10	70.43
results	162	David	Fecteau	Philadelphia	PA	48	M	119	121:04:50	55.54
results	163	Melody	Diehl	High Springs	FL	34	F	44	121:10:24	79.48
results	164	Matt	Watts	Kingman	AZ	39	M	120	121:21:17	57.98
results	165	James	Buesing	Peoria	AZ	47	M	121	121:27:23	54.89
results	166	Krista	Wilhelmson	Duluth	MN	44	F	45	121:35:46	73.21
results	167	Tracey	Saxey	Clearfield	UT	57	F	46	121:37:10	66.17
results	168	Robert	Ivan	Raritan	NJ	47	M	122	121:40:21	77.62
results	169	Steven	Maclean	Boise	ID	30	M	123	121:49:58	66.7
results	170	Jason	Brock	Kaysville	UT	48	M	124	121:58:06	71.04
results	171	Erin	Linehan	Denver	CO	44	F	47	122:08:39	66.78
results	172	Ana	Robbins	Atlanta	GA	42	F	48	122:14:57	68.41
results	173	Stephanie	Irving	Trout Lake	WA	63	F	49	122:27:08	69.96
results	174	Tony	Gillham	Sterling	AK	43	M	125	122:31:33	56.79
results	175	Megan	Healy	Culver City	CA	47	F	50	122:33:09	69.96
results	176	Wynonna	Fulgham	Chandler	AZ	37	F	51	122:47:07	58.64
results	177	Greg	Secatero	Kayenta	AZ	50	M	126	122:53:48	60.87
results	178	Lee	Addams	Salt Lake City	UT	53	M	127	123:01:10	60.09
results	179	Missy	Hendricks	Queen Creek	AZ	37	F	52	123:02:21	60.19
results	180	Meghan	Walsh	Oakland	CA	39	F	53	123:12:38	71.2
results	181	Paul James	Johnson	Rochester Hills	MI	68	M	128	123:22:35	59.57
results	182	Shawn	Gipson	Eloy	AZ	54	M	129	123:25:48	52.3
results	183	Jennifer	Smithson	Virginia Beach	VA	51	F	54	123:29:19	80.78
results	184	T.J.	Ward	Morganville	NJ	40	M	130	123:29:22	60.65
results	185	Brent	Knott	Fernandina Beach	FL	36	M	131	123:29:24	53.02
results	186	Richard	Plumb	Phoenix	AZ	57	M	132	123:33:13	52.68
results	187	Jen	Novobilski	Anchorage	AK	50	F	55	123:38:47	66.92
results	188	Mark	Laferriere	Somersworth	NH	44	M	133	124:01:06	53.51
results	189	Day Anne	Cena	Prescott	AZ	47	F	56	124:01:40	64.53
results	190	George	Lind	Chandler	AZ	47	M	134	124:14:53	66.79
results	191	Jennifer	Parrish	Lake Stevens	WA	52	F	57	124:26:25	70.74
results	192	Elizabeth	Russ	Bloomfield Hills	MI	31	F	58	124:26:30	64.69
results	192	David	Toms	Raleigh	NC	49	M	135	124:26:30	51.91
"""
    
    # Parse and import the data
    lines = results_data.strip().split('\n')
    added_count = 0
    
    for line in lines:
        if not line.strip():
            continue
            
        parts = line.split('\t')
        if len(parts) < 10:
            continue
            
        try:
            # Parse the data
            place = int(parts[1]) if parts[1] != '0' else None
            first_name = parts[2]
            last_name = parts[3]
            city = parts[4] if parts[4] else None
            state = parts[5] if parts[5] else None
            age = int(parts[6]) if parts[6] else None
            gender = parts[7] if parts[7] in ['M', 'F'] else 'M'
            gender_place = int(parts[8]) if parts[8] != '0' else None
            time_str = parts[9]
            
            # Handle special cases
            if not first_name or not last_name:
                continue
                
            # Parse finish time
            finish_time_hours = parse_time(time_str)
            
            # Determine if this runner has splits available (check if they're in our existing data)
            splits_available = False
            splits_file_path = None
            
            # Check for our existing runners with splits
            full_name = f"{first_name.lower()} {last_name.lower()}"
            if full_name in ['dan green', 'finn melanson', 'jeff garmire']:
                splits_available = True
                splits_file_path = f'./data/{first_name.lower()}_{last_name.lower()}_cocodona_250_2025_strava_splits_complete.csv'
            
            # Set country based on state/province
            country = 'USA'
            if state in ['ON', 'BC', 'QC', 'AB']:  # Canadian provinces
                country = 'Canada'
            elif not state:  # International runners without state
                if city in ['Cape Town', 'Perth', 'Brisbane']:
                    country = 'South Africa' if city == 'Cape Town' else 'Australia'
                elif city == 'Shulan':
                    country = 'China'
                elif city == 'Nagykanizsa':
                    country = 'Hungary'
                elif city == 'Zamora':
                    country = 'Mexico'
                elif city == 'Uddevalla':
                    country = 'Sweden'
                elif city == 'Oyama Shi':
                    country = 'Japan'
                else:
                    country = 'USA'  # Default for unclear cases
            
            # Create or find the runner
            runner_id = db.get_or_create_runner(
                first_name=first_name,
                last_name=last_name,
                age=age,
                gender=gender,
                city=city,
                state=state,
                country=country
            )
            
            # Add race result
            result_id = db.add_race_result(
                race_id=race_id,
                runner_id=runner_id,
                bib_number=str(place) if place else None,
                finish_time_hours=finish_time_hours,
                finish_position=place,
                gender_position=gender_place,
                status='Finished' if finish_time_hours else 'DNF',
                splits_available=splits_available,
                splits_file_path=splits_file_path
            )
            
            added_count += 1
            
        except (ValueError, IndexError) as e:
            print(f"Error parsing line: {line[:50]}... - {e}")
            continue
    
    print(f"Successfully imported {added_count} runner results for Cocodona 250 2025")
    
    # Print sample of imported data
    runners = db.get_race_runners(race_id)
    print(f"\nTotal runners in database: {len(runners)}")
    print(f"Finishers: {len([r for r in runners if r['status'] == 'Finished'])}")
    print(f"DNF: {len([r for r in runners if r['status'] == 'DNF'])}")
    print(f"With detailed splits: {len([r for r in runners if r['splits_available']])}")
    
    print("\nTop 10 finishers:")
    print("-" * 90)
    for i, runner in enumerate(runners[:10]):
        if runner['finish_position']:
            splits_status = "✓" if runner['splits_available'] else "✗"
            print(f"{runner['finish_position']:3d}. {runner['first_name']} {runner['last_name']:20s} "
                  f"({runner['age']:2d}{runner['gender']}) - {runner['finish_time_hours']:5.1f}h - "
                  f"{runner['city'] or 'Unknown'}, {runner['state'] or '--'} [Splits: {splits_status}]")

if __name__ == "__main__":
    import_cocodona_2025_results()