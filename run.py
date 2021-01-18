from PIL import Image, ImageFilter, ImageEnhance, ImageDraw,ImageFont, ImageOps
import requests
from io import BytesIO
from bs4 import BeautifulSoup as bs
import sys
import re
import os
import unidecode
from datetime import datetime
import pprint

pp = pprint.PrettyPrinter(indent=4)

def slugfy(text):
    text = unidecode.unidecode(text).lower()
    return re.sub(r'[\W_]+', '-', text)

def get_player_data(url, filter):
    headers = {"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36"}

    html = requests.get(url, headers=headers)
    soup = bs(html.content, features="html.parser")

    player = soup.select('.dataMain > .dataTop > .dataName > h1 > b')[0].text
    name = player

    if filter:
        table = soup.select('.responsive-table > .grid-view > .items > tbody')[0]
        leagues = table.find_all('tr')

        for league in leagues:
            if league.td.img['title'] == filter:
                apps = 0 if league.find_all('td')[2].text == '-' else league.find_all('td')[2].text
                goals = 0 if league.find_all('td')[3].text == '-' else league.find_all('td')[3].text
                assists = 0 if league.find_all('td')[4].text == '-' else league.find_all('td')[4].text
    else:
        tfoot = soup.select('.responsive-table > .grid-view > .items > tfoot')[0]
        values = tfoot.find_all(True, {"class": re.compile("^(zentriert)$")})

        apps = values[0].text
        goals = values[1].text
        assists = values[2].text

    return {
        'apps': apps, 'goals': goals, 'assists': assists, 'player': player
    }

def get_image(image_url, player_url, filter, subtitle_text, folder_name, club):
    # Open the image
    response = requests.get(image_url)
    im = Image.open(BytesIO(response.content))

    #Resize
    im = im.resize((800, 800))

    # Check if img isn't RGBA format and then set a RGBA mode
    if im.mode != 'RGBA':
        im = im.convert('RGBA')

    #crop the image area 600x800
    crop_area = (100, 0, 700, 800)
    im = im.crop(crop_area)

    # get the w and h from img
    width, height = im.size

    # Create a new image
    gradient = Image.new('L', (1, height), color=0xFF)

    # Loop through the real image height
    for x in range(height):
        gradient.putpixel((0, -x), int(255 * (1 - 1. * float(x)/height)))

    #Apply the gradient to the full image
    alpha = gradient.resize(im.size)
    black_im = Image.new('RGBA', (width, height), color=0) # i.e. black
    black_im.putalpha(alpha)
    gradient_im = Image.alpha_composite(im, black_im)

    #Get the half height of the image
    height_footer = int(height / 2)
    gradient_footer = Image.new('L', (1, height_footer), color=0xFF)

    # Loop through the half image height, means the footer
    for x in range(height_footer):
        gradient_footer.putpixel((0, -x), int(255 * (1 - 1. * float(-x)/height_footer)))

    #Apply the gradient to the image footer
    alpha_footer = gradient.resize(im.size)
    black_im_footer = Image.new('RGBA', (width, height), color=0) # i.e. black
    black_im_footer.putalpha(alpha_footer)
    output = Image.alpha_composite(gradient_im, black_im_footer)

    #Apply the Data Science logo
    logo = Image.open('./images/logo.png')
    logo = logo.resize((75, 75))
    output.paste(logo, (10, 10), logo)

    #Get the player stats
    stats = get_player_data(player_url, filter)


    if club:
        response = requests.get(club)
        shield = Image.open(BytesIO(response.content))
        shield = shield.resize((125, 125))
        # output.paste(shield, (275, 500), shield)
        output.paste(shield, (int((width-125)/2), 425), shield)


    #writing text
    title = stats['player']
    subtitle = subtitle_text
    apps = stats['apps']
    goals = stats['goals']
    assists = stats['assists']
    apps_text = 'Apps'
    goals_text = 'Goals'
    assists_text = 'Assists'

    title_font = ImageFont.truetype('./fonts/Lato-Bold.ttf', 60)
    medium_font = ImageFont.truetype('./fonts/Lato-Bold.ttf', 30)
    subtitle_font = ImageFont.truetype('./fonts/Lato-Light.ttf', 19)

    draw = ImageDraw.Draw(output)
    title_width, title_height = draw.textsize(title, font=title_font)
    draw.text(((width-title_width)/2,((height-title_height)/2)+200), title, font=title_font, fill="white")

    subtitle_width, subtitle_height = draw.textsize(subtitle, font=subtitle_font)
    draw.text(((width-subtitle_width)/2,((height-subtitle_height)/2)+250), subtitle, font=subtitle_font, fill="white")

    #Apps text and number
    apps_width, apps_height = draw.textsize(apps, font=medium_font)
    draw.text((((width-apps_width)/2-100),((height-apps_height)/2)+300), apps, font=medium_font, fill="white")

    apps_text_width, apps_text_height = draw.textsize(apps_text, font=subtitle_font)
    draw.text((((width-apps_text_width)/2-100),((height-apps_text_height)/2)+325), apps_text, align='center', font=subtitle_font, fill="white")

    #Goals text and number
    goals_width, goals_height = draw.textsize(apps, font=medium_font)
    draw.text((((width-goals_width)/2),((height-goals_height)/2)+300), goals, font=medium_font, fill="white")

    goals_text_width, goals_text_height = draw.textsize(goals_text, font=subtitle_font)
    draw.text((((width-goals_text_width)/2),((height-goals_text_height)/2)+325), goals_text, font=subtitle_font, fill="white")

    #Assists text and number
    assists_width, assists_height = draw.textsize(assists, font=medium_font)
    draw.text((((width-assists_width)/2+100),((height-assists_height)/2)+300), assists, font=medium_font, fill="white")

    assists_text_width, assists_text_height = draw.textsize(assists_text, font=subtitle_font)
    draw.text((((width-assists_text_width)/2+100),((height-assists_text_height)/2)+325), assists_text, font=subtitle_font, fill="white")


    folder = folder_name
    folder = './images/' + slugfy(folder)

    if not os.path.exists(folder):
        os.makedirs(folder)

    out_file = f"{folder}/{slugfy(stats['player'])}-{slugfy(subtitle_text)}.png"
    print(out_file)

    output.save(out_file)

players = [
    {
        'photo': 'https://i2-prod.leicestermercury.co.uk/sport/football/article3665184.ece/ALTERNATES/s1200c/0_Jamie-Vardy-135.jpg',
        'profile': 'https://www.transfermarkt.com/jamie-vardy/leistungsdaten/spieler/197838/plus/0?saison=2019',
        'text': '2019/2020 Season',
        'filter': 'Premier League',
        'club': 'https://www.logolynx.com/images/logolynx/ea/ea9a36d2fef41a3029426d903d2e8f1b.png'
    },
    {
        'photo': 'https://i2-prod.birminghammail.co.uk/incoming/article18026262.ece/ALTERNATES/s1200c/0_Pierre-Emerick-Aubameyang.jpg',
        'profile': 'https://www.transfermarkt.com/jamie-vardy/leistungsdaten/spieler/58864/plus/0?saison=2018',
        'text': '2018/2019 Season',
        'filter': 'Premier League',
        'club': 'https://www.logolynx.com/images/logolynx/f5/f50109ec24e2633aff48c3b332c00170.png'
    },
    {
        'photo': 'https://i.pinimg.com/originals/e6/34/27/e63427dc38816f1559f71aa67e1ac800.jpg',
        'profile': 'https://www.transfermarkt.com/sadio-mane/leistungsdaten/spieler/200512/plus/0?saison=2018',
        'text': '2018/2019 Season',
        'filter': 'Premier League',
        'club': 'https://www.logolynx.com/images/logolynx/f4/f4ed1490eb89a7dfc2bc48a48ec55c84.png'
    },
    {
        'photo': 'https://i.guim.co.uk/img/media/ddab8e3e1ba5a0afe7bf30596ce0f0a505802e8e/304_0_2857_1714/master/2857.jpg?width=1200&height=1200&quality=85&auto=format&fit=crop&s=968e3f614b1180c77212736b1e0664b6',
        'profile': 'https://www.transfermarkt.com/mohamed-salah/leistungsdaten/spieler/148455/plus/0?saison=2018',
        'text': '2018/2019 Season',
        'filter': 'Premier League',
        'club': 'https://www.logolynx.com/images/logolynx/f4/f4ed1490eb89a7dfc2bc48a48ec55c84.png'
    },
    {
        'photo': 'https://amayei.nyc3.digitaloceanspaces.com/2018/09/salah-18.jpg',
        'profile': 'https://www.transfermarkt.com/mohamed-salah/leistungsdaten/spieler/148455/plus/0?saison=2017',
        'text': '2017/2018 Season',
        'filter': 'Premier League',
        'club': 'https://www.logolynx.com/images/logolynx/f4/f4ed1490eb89a7dfc2bc48a48ec55c84.png'
    },
    {
        'photo': 'https://media.bleacherreport.com/f_auto,w_800,h_800,q_auto,c_fill/br-img-images/003/234/438/b1b8f1b7ce322d987526a8f6e19b07e3_crop_north.jpg',
        'profile': 'https://www.transfermarkt.com/harry-kane/leistungsdaten/spieler/132098/plus/0?saison=2016',
        'text': '2016/2017 Season',
        'filter': 'Premier League',
        'club': 'https://www.logolynx.com/images/logolynx/20/2072a637d6dd5bae3e500bcdeb35ce04.png'
    },
    {
        'photo': 'https://img.bleacherreport.net/img/images/photos/003/585/229/hi-res-8ac7e8a1673c9e6f27813a2e7f299720_crop_exact.jpg?w=1200&h=1200&q=75',
        'profile': 'https://www.transfermarkt.com/harry-kane/leistungsdaten/spieler/132098/plus/0?saison=2015',
        'text': '2015/2016 Season',
        'filter': 'Premier League',
        'club': 'https://www.logolynx.com/images/logolynx/20/2072a637d6dd5bae3e500bcdeb35ce04.png'
    },
    {
        'photo': 'https://i2-prod.manchestereveningnews.co.uk/incoming/article9321824.ece/ALTERNATES/s1200c/1_aguero.jpg',
        'profile': 'https://www.transfermarkt.com/sergio-aguero/leistungsdaten/spieler/26399/plus/0?saison=2014',
        'text': '2014/2015 Season',
        'filter': 'Premier League',
        'club': 'https://www.logolynx.com/images/logolynx/s_02/0273fa5940eab11efd0e3f3eb3f1fe13.png'
    },
    {
        'photo': 'https://img.bleacherreport.net/img/images/photos/002/696/777/hi-res-459715843-luis-suarez-of-liverpool-looks-on-during-the-barclays_crop_exact.jpg?w=1200&h=1200&q=50',
        'profile': 'https://www.transfermarkt.com/luis-suarez/leistungsdaten/spieler/44352/plus/0?saison=2013',
        'text': '2013/2014 Season',
        'filter': 'Premier League',
        'club': 'https://www.logolynx.com/images/logolynx/f4/f4ed1490eb89a7dfc2bc48a48ec55c84.png'
    },
    {
        'photo': 'https://pbs.twimg.com/media/BR5B6eECQAA9vMD.jpg:large',
        'profile': 'https://www.transfermarkt.com/robin-van-persie/leistungsdaten/spieler/4380/plus/0?saison=2012',
        'text': '2012/2013 Season',
        'filter': 'Premier League',
        'club': 'https://www.logolynx.com/images/logolynx/4b/4bbdcec5ae3d524571c1ef4d08b4a0c5.png'
    },
    {
        'photo': 'https://img.bleacherreport.net/img/images/photos/001/698/146/140787468_crop_exact.jpg?w=1200&h=1200&q=75',
        'profile': 'https://www.transfermarkt.com/robin-van-persie/leistungsdaten/spieler/4380/plus/0?saison=2011',
        'text': '2011/2012 Season',
        'filter': 'Premier League',
        'club': 'https://www.logolynx.com/images/logolynx/f5/f50109ec24e2633aff48c3b332c00170.png'
    },
    {
        'photo': 'https://cdn.vox-cdn.com/thumbor/_WzT3lBa6D8TGArzOvKEYq6J9lw=/0x0:599x399/1400x1400/filters:focal(0x0:599x399):format(jpeg)/cdn.vox-cdn.com/photo_images/1034103/GYI0061260922.jpg',
        'profile': 'https://www.transfermarkt.com/dimitar-berbatov/leistungsdaten/spieler/65/plus/0?saison=2010',
        'text': '2010/2011 Season',
        'filter': 'Premier League',
        'club': 'https://www.logolynx.com/images/logolynx/4b/4bbdcec5ae3d524571c1ef4d08b4a0c5.png'
    },
    {
        'photo': 'https://media.bleacherreport.com/f_auto,w_800,h_800,q_auto,c_fill/br-img-images/003/639/593/hi-res-fd8369d335bdceb402b4ecf7c08d778c_crop_north.jpg',
        'profile': 'https://www.transfermarkt.com/carlos-tevez/leistungsdaten/spieler/4276/plus/0?saison=2010',
        'text': '2010/2011 Season',
        'filter': 'Premier League',
        'club': 'https://www.logolynx.com/images/logolynx/s_02/0273fa5940eab11efd0e3f3eb3f1fe13.png'
    }
]


for player in players:
    get_image(player['photo'], player['profile'], player['filter'], player['text'], 'last-pl-scorers', player['club'])