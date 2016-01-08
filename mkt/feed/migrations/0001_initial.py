# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import mkt.site.fields
import mkt.constants.carriers
import mkt.ratings.validators
import mkt.feed.models
import mkt.constants.regions


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='FeedApp',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('image_hash', models.CharField(default=None, max_length=8, null=True, blank=True)),
                ('slug', models.CharField(unique=True, max_length=30)),
                ('color', models.CharField(max_length=20, null=True, blank=True)),
                ('type', models.CharField(max_length=30, choices=[(b'icon', b'icon'), (b'image', b'image'), (b'description', b'description'), (b'quote', b'quote'), (b'preview', b'preview')])),
                ('pullquote_attribution', models.CharField(max_length=50, null=True, blank=True)),
                ('pullquote_rating', models.PositiveSmallIntegerField(blank=True, null=True, validators=[mkt.ratings.validators.validate_rating])),
                ('background_color', mkt.site.fields.ColorField(max_length=7, null=True)),
            ],
            options={
                'db_table': 'mkt_feed_app',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FeedBrand',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('slug', models.CharField(help_text=b'Used in collection URLs.', unique=True, max_length=30, blank=True)),
                ('layout', models.CharField(max_length=30, choices=[(b'grid', b'grid'), (b'list', b'list')])),
                ('type', models.CharField(max_length=30, choices=[(b'apps-for-albania', b'apps-for-albania'), (b'apps-for-argentina', b'apps-for-argentina'), (b'apps-for-bangladesh', b'apps-for-bangladesh'), (b'apps-for-brazil', b'apps-for-brazil'), (b'apps-for-bulgaria', b'apps-for-bulgaria'), (b'apps-for-chile', b'apps-for-chile'), (b'apps-for-china', b'apps-for-china'), (b'apps-for-colombia', b'apps-for-colombia'), (b'apps-for-costa-rica', b'apps-for-costa-rica'), (b'apps-for-croatia', b'apps-for-croatia'), (b'apps-for-czech-republic', b'apps-for-czech-republic'), (b'apps-for-ecuador', b'apps-for-ecuador'), (b'apps-for-el-salvador', b'apps-for-el-salvador'), (b'apps-for-france', b'apps-for-france'), (b'apps-for-germany', b'apps-for-germany'), (b'apps-for-greece', b'apps-for-greece'), (b'apps-for-hungary', b'apps-for-hungary'), (b'apps-for-india', b'apps-for-india'), (b'apps-for-italy', b'apps-for-italy'), (b'apps-for-japan', b'apps-for-japan'), (b'apps-for-macedonia', b'apps-for-macedonia'), (b'apps-for-mexico', b'apps-for-mexico'), (b'apps-for-montenegro', b'apps-for-montenegro'), (b'apps-for-nicaragua', b'apps-for-nicaragua'), (b'apps-for-panama', b'apps-for-panama'), (b'apps-for-peru', b'apps-for-peru'), (b'apps-for-poland', b'apps-for-poland'), (b'apps-for-russia', b'apps-for-russia'), (b'apps-for-serbia', b'apps-for-serbia'), (b'apps-for-south-africa', b'apps-for-south-africa'), (b'apps-for-spain', b'apps-for-spain'), (b'apps-for-uruguay', b'apps-for-uruguay'), (b'apps-for-venezuela', b'apps-for-venezuela'), (b'arts-entertainment', b'arts-entertainment'), (b'book', b'book'), (b'creativity', b'creativity'), (b'education', b'education'), (b'games', b'games'), (b'groundbreaking', b'groundbreaking'), (b'health-fitness', b'health-fitness'), (b'hidden-gem', b'hidden-gem'), (b'lifestyle', b'lifestyle'), (b'local-favorite', b'local-favorite'), (b'maps-navigation', b'maps-navigation'), (b'music', b'music'), (b'mystery-app', b'mystery-app'), (b'news-weather', b'news-weather'), (b'photo-video', b'photo-video'), (b'shopping', b'shopping'), (b'social', b'social'), (b'sports', b'sports'), (b'tools-time-savers', b'tools-time-savers'), (b'travel', b'travel'), (b'work-business', b'work-business')])),
            ],
            options={
                'ordering': ('-id',),
                'abstract': False,
                'db_table': 'mkt_feed_brand',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FeedBrandMembership',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('order', models.SmallIntegerField(null=True)),
            ],
            options={
                'ordering': ('order',),
                'abstract': False,
                'db_table': 'mkt_feed_brand_membership',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FeedCollection',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('slug', models.CharField(help_text=b'Used in collection URLs.', unique=True, max_length=30, blank=True)),
                ('image_hash', models.CharField(default=None, max_length=8, null=True, blank=True)),
                ('color', models.CharField(max_length=20, null=True, blank=True)),
                ('type', models.CharField(max_length=30, null=True, choices=[(b'promo', b'promo'), (b'listing', b'listing')])),
                ('background_color', models.CharField(max_length=7, null=True, blank=True)),
            ],
            options={
                'ordering': ('-id',),
                'abstract': False,
                'db_table': 'mkt_feed_collection',
            },
            bases=(mkt.feed.models.GroupedAppsMixin, models.Model),
        ),
        migrations.CreateModel(
            name='FeedCollectionMembership',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('order', models.SmallIntegerField(null=True)),
            ],
            options={
                'ordering': ('order',),
                'abstract': False,
                'db_table': 'mkt_feed_collection_membership',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FeedItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('category', models.CharField(blank=True, max_length=30, null=True, choices=[(b'books-comics', 'Books & Comics'), (b'business', 'Business'), (b'education', 'Education'), (b'entertainment', 'Entertainment'), (b'food-drink', 'Food & Drink'), (b'kids', 'Kids'), (b'games', 'Games'), (b'health-fitness', 'Health & Fitness'), (b'humor', 'Humor'), (b'internet', 'Internet'), (b'lifestyle', 'Lifestyle'), (b'maps-navigation', 'Maps & Navigation'), (b'music', 'Music'), (b'news', 'News'), (b'personalization', 'Personalization'), (b'photo-video', 'Photo & Video'), (b'productivity', 'Productivity'), (b'reference', 'Reference'), (b'science-tech', 'Science & Tech'), (b'shopping', 'Shopping'), (b'social', 'Social'), (b'sports', 'Sports'), (b'travel', 'Travel'), (b'utilities', 'Utilities'), (b'weather', 'Weather')])),
                ('region', models.PositiveIntegerField(default=None, null=True, db_index=True, blank=True, choices=[(1, mkt.constants.regions.RESTOFWORLD), (63, mkt.constants.regions.AND), (241, mkt.constants.regions.ARE), (58, mkt.constants.regions.AFG), (67, mkt.constants.regions.ATG), (65, mkt.constants.regions.AIA), (60, mkt.constants.regions.ALB), (68, mkt.constants.regions.ARM), (64, mkt.constants.regions.AGO), (66, mkt.constants.regions.ATA), (20, mkt.constants.regions.ARG), (62, mkt.constants.regions.ASM), (71, mkt.constants.regions.AUT), (70, mkt.constants.regions.AUS), (69, mkt.constants.regions.ABW), (59, mkt.constants.regions.ALA), (72, mkt.constants.regions.AZE), (84, mkt.constants.regions.BIH), (75, mkt.constants.regions.BRB), (31, mkt.constants.regions.BGD), (77, mkt.constants.regions.BEL), (89, mkt.constants.regions.BFA), (88, mkt.constants.regions.BGR), (74, mkt.constants.regions.BHR), (90, mkt.constants.regions.BDI), (79, mkt.constants.regions.BEN), (253, mkt.constants.regions.BLM), (80, mkt.constants.regions.BMU), (87, mkt.constants.regions.BRN), (82, mkt.constants.regions.BOL), (252, mkt.constants.regions.BES), (7, mkt.constants.regions.BRA), (73, mkt.constants.regions.BHS), (81, mkt.constants.regions.BTN), (85, mkt.constants.regions.BVT), (45, mkt.constants.regions.BWA), (76, mkt.constants.regions.BLR), (78, mkt.constants.regions.BLZ), (92, mkt.constants.regions.CAN), (97, mkt.constants.regions.CCK), (100, mkt.constants.regions.COD), (54, mkt.constants.regions.CAF), (99, mkt.constants.regions.COG), (226, mkt.constants.regions.CHE), (40, mkt.constants.regions.CIV), (101, mkt.constants.regions.COK), (23, mkt.constants.regions.CHL), (42, mkt.constants.regions.CMR), (21, mkt.constants.regions.CHN), (9, mkt.constants.regions.COL), (27, mkt.constants.regions.CRI), (103, mkt.constants.regions.CUB), (93, mkt.constants.regions.CPV), (254, mkt.constants.regions.CUW), (96, mkt.constants.regions.CXR), (105, mkt.constants.regions.CYP), (34, mkt.constants.regions.CZE), (14, mkt.constants.regions.DEU), (107, mkt.constants.regions.DJI), (106, mkt.constants.regions.DNK), (108, mkt.constants.regions.DMA), (109, mkt.constants.regions.DOM), (61, mkt.constants.regions.DZA), (26, mkt.constants.regions.ECU), (112, mkt.constants.regions.EST), (43, mkt.constants.regions.EGY), (248, mkt.constants.regions.ESH), (111, mkt.constants.regions.ERI), (8, mkt.constants.regions.ESP), (113, mkt.constants.regions.ETH), (117, mkt.constants.regions.FIN), (116, mkt.constants.regions.FJI), (114, mkt.constants.regions.FLK), (168, mkt.constants.regions.FSM), (115, mkt.constants.regions.FRO), (30, mkt.constants.regions.FRA), (121, mkt.constants.regions.GAB), (127, mkt.constants.regions.GRD), (123, mkt.constants.regions.GEO), (118, mkt.constants.regions.GUF), (130, mkt.constants.regions.GGY), (124, mkt.constants.regions.GHA), (125, mkt.constants.regions.GIB), (126, mkt.constants.regions.GRL), (122, mkt.constants.regions.GMB), (55, mkt.constants.regions.GIN), (128, mkt.constants.regions.GLP), (110, mkt.constants.regions.GNQ), (17, mkt.constants.regions.GRC), (218, mkt.constants.regions.SGS), (25, mkt.constants.regions.GTM), (129, mkt.constants.regions.GUM), (46, mkt.constants.regions.GNB), (131, mkt.constants.regions.GUY), (136, mkt.constants.regions.HKG), (133, mkt.constants.regions.HMD), (135, mkt.constants.regions.HND), (102, mkt.constants.regions.HRV), (132, mkt.constants.regions.HTI), (13, mkt.constants.regions.HUN), (138, mkt.constants.regions.IDN), (140, mkt.constants.regions.IRL), (142, mkt.constants.regions.ISR), (141, mkt.constants.regions.IMN), (32, mkt.constants.regions.IND), (86, mkt.constants.regions.IOT), (139, mkt.constants.regions.IRQ), (137, mkt.constants.regions.ISL), (22, mkt.constants.regions.ITA), (144, mkt.constants.regions.JEY), (143, mkt.constants.regions.JAM), (51, mkt.constants.regions.JOR), (33, mkt.constants.regions.JPN), (56, mkt.constants.regions.KEN), (149, mkt.constants.regions.KGZ), (91, mkt.constants.regions.KHM), (146, mkt.constants.regions.KIR), (98, mkt.constants.regions.COM), (201, mkt.constants.regions.KNA), (147, mkt.constants.regions.KOR), (148, mkt.constants.regions.KWT), (94, mkt.constants.regions.CYM), (145, mkt.constants.regions.KAZ), (150, mkt.constants.regions.LAO), (152, mkt.constants.regions.LBN), (202, mkt.constants.regions.LCA), (156, mkt.constants.regions.LIE), (220, mkt.constants.regions.LKA), (154, mkt.constants.regions.LBR), (153, mkt.constants.regions.LSO), (38, mkt.constants.regions.LTU), (157, mkt.constants.regions.LUX), (151, mkt.constants.regions.LVA), (155, mkt.constants.regions.LBY), (173, mkt.constants.regions.MAR), (170, mkt.constants.regions.MCO), (169, mkt.constants.regions.MDA), (15, mkt.constants.regions.MNE), (255, mkt.constants.regions.MAF), (49, mkt.constants.regions.MDG), (164, mkt.constants.regions.MHL), (159, mkt.constants.regions.MKD), (48, mkt.constants.regions.MLI), (53, mkt.constants.regions.MMR), (171, mkt.constants.regions.MNG), (158, mkt.constants.regions.MAC), (184, mkt.constants.regions.MNP), (165, mkt.constants.regions.MTQ), (166, mkt.constants.regions.MRT), (172, mkt.constants.regions.MSR), (163, mkt.constants.regions.MLT), (50, mkt.constants.regions.MUS), (162, mkt.constants.regions.MDV), (160, mkt.constants.regions.MWI), (12, mkt.constants.regions.MEX), (161, mkt.constants.regions.MYS), (174, mkt.constants.regions.MOZ), (175, mkt.constants.regions.NAM), (179, mkt.constants.regions.NCL), (52, mkt.constants.regions.NER), (183, mkt.constants.regions.NFK), (181, mkt.constants.regions.NGA), (29, mkt.constants.regions.NIC), (178, mkt.constants.regions.NLD), (185, mkt.constants.regions.NOR), (177, mkt.constants.regions.NPL), (176, mkt.constants.regions.NRU), (182, mkt.constants.regions.NIU), (180, mkt.constants.regions.NZL), (186, mkt.constants.regions.OMN), (28, mkt.constants.regions.PAN), (18, mkt.constants.regions.PER), (119, mkt.constants.regions.PYF), (190, mkt.constants.regions.PNG), (35, mkt.constants.regions.PHL), (187, mkt.constants.regions.PAK), (11, mkt.constants.regions.POL), (204, mkt.constants.regions.SPM), (192, mkt.constants.regions.PCN), (194, mkt.constants.regions.PRI), (189, mkt.constants.regions.PSE), (193, mkt.constants.regions.PRT), (188, mkt.constants.regions.PLW), (191, mkt.constants.regions.PRY), (195, mkt.constants.regions.QAT), (196, mkt.constants.regions.REU), (197, mkt.constants.regions.ROU), (16, mkt.constants.regions.SRB), (36, mkt.constants.regions.RUS), (198, mkt.constants.regions.RWA), (209, mkt.constants.regions.SAU), (216, mkt.constants.regions.SLB), (210, mkt.constants.regions.SYC), (221, mkt.constants.regions.SDN), (225, mkt.constants.regions.SWE), (212, mkt.constants.regions.SGP), (200, mkt.constants.regions.SHN), (215, mkt.constants.regions.SVN), (223, mkt.constants.regions.SJM), (214, mkt.constants.regions.SVK), (211, mkt.constants.regions.SLE), (207, mkt.constants.regions.SMR), (41, mkt.constants.regions.SEN), (217, mkt.constants.regions.SOM), (222, mkt.constants.regions.SUR), (219, mkt.constants.regions.SSD), (208, mkt.constants.regions.STP), (24, mkt.constants.regions.SLV), (256, mkt.constants.regions.SXM), (227, mkt.constants.regions.SYR), (224, mkt.constants.regions.SWZ), (237, mkt.constants.regions.TCA), (95, mkt.constants.regions.TCD), (120, mkt.constants.regions.ATF), (231, mkt.constants.regions.TGO), (229, mkt.constants.regions.THA), (228, mkt.constants.regions.TJK), (232, mkt.constants.regions.TKL), (230, mkt.constants.regions.TLS), (236, mkt.constants.regions.TKM), (39, mkt.constants.regions.TUN), (233, mkt.constants.regions.TON), (235, mkt.constants.regions.TUR), (234, mkt.constants.regions.TTO), (238, mkt.constants.regions.TUV), (57, mkt.constants.regions.TWN), (44, mkt.constants.regions.TZA), (240, mkt.constants.regions.UKR), (239, mkt.constants.regions.UGA), (4, mkt.constants.regions.GBR), (257, mkt.constants.regions.UMI), (2, mkt.constants.regions.USA), (19, mkt.constants.regions.URY), (243, mkt.constants.regions.UZB), (134, mkt.constants.regions.VAT), (205, mkt.constants.regions.VCT), (10, mkt.constants.regions.VEN), (245, mkt.constants.regions.VGB), (246, mkt.constants.regions.VIR), (244, mkt.constants.regions.VNM), (47, mkt.constants.regions.VUT), (247, mkt.constants.regions.WLF), (206, mkt.constants.regions.WSM), (249, mkt.constants.regions.YEM), (167, mkt.constants.regions.MYT), (37, mkt.constants.regions.ZAF), (250, mkt.constants.regions.ZMB), (251, mkt.constants.regions.ZWE)])),
                ('carrier', models.IntegerField(default=None, null=True, db_index=True, blank=True, choices=[(15, mkt.constants.carriers.TELENOR), (7, mkt.constants.carriers.KDDI), (11, mkt.constants.carriers.SINGTEL), (13, mkt.constants.carriers.SPRINT), (14, mkt.constants.carriers.TELECOM_ITALIA_GROUP), (17, mkt.constants.carriers.VIMPELCOM), (9, mkt.constants.carriers.MEGAFON), (2, mkt.constants.carriers.AMERICA_MOVIL), (6, mkt.constants.carriers.HUTCHINSON_THREE_GROUP), (19, mkt.constants.carriers.CONGSTAR), (22, mkt.constants.carriers.ORANGE), (21, mkt.constants.carriers.MTN), (0, mkt.constants.carriers.UNKNOWN_CARRIER), (20, mkt.constants.carriers.O2), (12, mkt.constants.carriers.SMART), (5, mkt.constants.carriers.ETISALAT), (18, mkt.constants.carriers.GRAMEENPHONE), (8, mkt.constants.carriers.KT), (10, mkt.constants.carriers.QTEL), (3, mkt.constants.carriers.CHINA_UNICOM), (1, mkt.constants.carriers.TELEFONICA), (16, mkt.constants.carriers.TMN), (4, mkt.constants.carriers.DEUTSCHE_TELEKOM)])),
                ('order', models.SmallIntegerField(null=True)),
                ('item_type', models.CharField(max_length=30)),
            ],
            options={
                'ordering': ('order',),
                'db_table': 'mkt_feed_item',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FeedShelf',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('slug', models.CharField(help_text=b'Used in collection URLs.', unique=True, max_length=30, blank=True)),
                ('image_hash', models.CharField(default=None, max_length=8, null=True, blank=True)),
                ('carrier', models.IntegerField(choices=[(15, mkt.constants.carriers.TELENOR), (7, mkt.constants.carriers.KDDI), (11, mkt.constants.carriers.SINGTEL), (13, mkt.constants.carriers.SPRINT), (14, mkt.constants.carriers.TELECOM_ITALIA_GROUP), (17, mkt.constants.carriers.VIMPELCOM), (9, mkt.constants.carriers.MEGAFON), (2, mkt.constants.carriers.AMERICA_MOVIL), (6, mkt.constants.carriers.HUTCHINSON_THREE_GROUP), (19, mkt.constants.carriers.CONGSTAR), (22, mkt.constants.carriers.ORANGE), (21, mkt.constants.carriers.MTN), (0, mkt.constants.carriers.UNKNOWN_CARRIER), (20, mkt.constants.carriers.O2), (12, mkt.constants.carriers.SMART), (5, mkt.constants.carriers.ETISALAT), (18, mkt.constants.carriers.GRAMEENPHONE), (8, mkt.constants.carriers.KT), (10, mkt.constants.carriers.QTEL), (3, mkt.constants.carriers.CHINA_UNICOM), (1, mkt.constants.carriers.TELEFONICA), (16, mkt.constants.carriers.TMN), (4, mkt.constants.carriers.DEUTSCHE_TELEKOM)])),
                ('region', models.PositiveIntegerField(choices=[(1, mkt.constants.regions.RESTOFWORLD), (63, mkt.constants.regions.AND), (241, mkt.constants.regions.ARE), (58, mkt.constants.regions.AFG), (67, mkt.constants.regions.ATG), (65, mkt.constants.regions.AIA), (60, mkt.constants.regions.ALB), (68, mkt.constants.regions.ARM), (64, mkt.constants.regions.AGO), (66, mkt.constants.regions.ATA), (20, mkt.constants.regions.ARG), (62, mkt.constants.regions.ASM), (71, mkt.constants.regions.AUT), (70, mkt.constants.regions.AUS), (69, mkt.constants.regions.ABW), (59, mkt.constants.regions.ALA), (72, mkt.constants.regions.AZE), (84, mkt.constants.regions.BIH), (75, mkt.constants.regions.BRB), (31, mkt.constants.regions.BGD), (77, mkt.constants.regions.BEL), (89, mkt.constants.regions.BFA), (88, mkt.constants.regions.BGR), (74, mkt.constants.regions.BHR), (90, mkt.constants.regions.BDI), (79, mkt.constants.regions.BEN), (253, mkt.constants.regions.BLM), (80, mkt.constants.regions.BMU), (87, mkt.constants.regions.BRN), (82, mkt.constants.regions.BOL), (252, mkt.constants.regions.BES), (7, mkt.constants.regions.BRA), (73, mkt.constants.regions.BHS), (81, mkt.constants.regions.BTN), (85, mkt.constants.regions.BVT), (45, mkt.constants.regions.BWA), (76, mkt.constants.regions.BLR), (78, mkt.constants.regions.BLZ), (92, mkt.constants.regions.CAN), (97, mkt.constants.regions.CCK), (100, mkt.constants.regions.COD), (54, mkt.constants.regions.CAF), (99, mkt.constants.regions.COG), (226, mkt.constants.regions.CHE), (40, mkt.constants.regions.CIV), (101, mkt.constants.regions.COK), (23, mkt.constants.regions.CHL), (42, mkt.constants.regions.CMR), (21, mkt.constants.regions.CHN), (9, mkt.constants.regions.COL), (27, mkt.constants.regions.CRI), (103, mkt.constants.regions.CUB), (93, mkt.constants.regions.CPV), (254, mkt.constants.regions.CUW), (96, mkt.constants.regions.CXR), (105, mkt.constants.regions.CYP), (34, mkt.constants.regions.CZE), (14, mkt.constants.regions.DEU), (107, mkt.constants.regions.DJI), (106, mkt.constants.regions.DNK), (108, mkt.constants.regions.DMA), (109, mkt.constants.regions.DOM), (61, mkt.constants.regions.DZA), (26, mkt.constants.regions.ECU), (112, mkt.constants.regions.EST), (43, mkt.constants.regions.EGY), (248, mkt.constants.regions.ESH), (111, mkt.constants.regions.ERI), (8, mkt.constants.regions.ESP), (113, mkt.constants.regions.ETH), (117, mkt.constants.regions.FIN), (116, mkt.constants.regions.FJI), (114, mkt.constants.regions.FLK), (168, mkt.constants.regions.FSM), (115, mkt.constants.regions.FRO), (30, mkt.constants.regions.FRA), (121, mkt.constants.regions.GAB), (127, mkt.constants.regions.GRD), (123, mkt.constants.regions.GEO), (118, mkt.constants.regions.GUF), (130, mkt.constants.regions.GGY), (124, mkt.constants.regions.GHA), (125, mkt.constants.regions.GIB), (126, mkt.constants.regions.GRL), (122, mkt.constants.regions.GMB), (55, mkt.constants.regions.GIN), (128, mkt.constants.regions.GLP), (110, mkt.constants.regions.GNQ), (17, mkt.constants.regions.GRC), (218, mkt.constants.regions.SGS), (25, mkt.constants.regions.GTM), (129, mkt.constants.regions.GUM), (46, mkt.constants.regions.GNB), (131, mkt.constants.regions.GUY), (136, mkt.constants.regions.HKG), (133, mkt.constants.regions.HMD), (135, mkt.constants.regions.HND), (102, mkt.constants.regions.HRV), (132, mkt.constants.regions.HTI), (13, mkt.constants.regions.HUN), (138, mkt.constants.regions.IDN), (140, mkt.constants.regions.IRL), (142, mkt.constants.regions.ISR), (141, mkt.constants.regions.IMN), (32, mkt.constants.regions.IND), (86, mkt.constants.regions.IOT), (139, mkt.constants.regions.IRQ), (137, mkt.constants.regions.ISL), (22, mkt.constants.regions.ITA), (144, mkt.constants.regions.JEY), (143, mkt.constants.regions.JAM), (51, mkt.constants.regions.JOR), (33, mkt.constants.regions.JPN), (56, mkt.constants.regions.KEN), (149, mkt.constants.regions.KGZ), (91, mkt.constants.regions.KHM), (146, mkt.constants.regions.KIR), (98, mkt.constants.regions.COM), (201, mkt.constants.regions.KNA), (147, mkt.constants.regions.KOR), (148, mkt.constants.regions.KWT), (94, mkt.constants.regions.CYM), (145, mkt.constants.regions.KAZ), (150, mkt.constants.regions.LAO), (152, mkt.constants.regions.LBN), (202, mkt.constants.regions.LCA), (156, mkt.constants.regions.LIE), (220, mkt.constants.regions.LKA), (154, mkt.constants.regions.LBR), (153, mkt.constants.regions.LSO), (38, mkt.constants.regions.LTU), (157, mkt.constants.regions.LUX), (151, mkt.constants.regions.LVA), (155, mkt.constants.regions.LBY), (173, mkt.constants.regions.MAR), (170, mkt.constants.regions.MCO), (169, mkt.constants.regions.MDA), (15, mkt.constants.regions.MNE), (255, mkt.constants.regions.MAF), (49, mkt.constants.regions.MDG), (164, mkt.constants.regions.MHL), (159, mkt.constants.regions.MKD), (48, mkt.constants.regions.MLI), (53, mkt.constants.regions.MMR), (171, mkt.constants.regions.MNG), (158, mkt.constants.regions.MAC), (184, mkt.constants.regions.MNP), (165, mkt.constants.regions.MTQ), (166, mkt.constants.regions.MRT), (172, mkt.constants.regions.MSR), (163, mkt.constants.regions.MLT), (50, mkt.constants.regions.MUS), (162, mkt.constants.regions.MDV), (160, mkt.constants.regions.MWI), (12, mkt.constants.regions.MEX), (161, mkt.constants.regions.MYS), (174, mkt.constants.regions.MOZ), (175, mkt.constants.regions.NAM), (179, mkt.constants.regions.NCL), (52, mkt.constants.regions.NER), (183, mkt.constants.regions.NFK), (181, mkt.constants.regions.NGA), (29, mkt.constants.regions.NIC), (178, mkt.constants.regions.NLD), (185, mkt.constants.regions.NOR), (177, mkt.constants.regions.NPL), (176, mkt.constants.regions.NRU), (182, mkt.constants.regions.NIU), (180, mkt.constants.regions.NZL), (186, mkt.constants.regions.OMN), (28, mkt.constants.regions.PAN), (18, mkt.constants.regions.PER), (119, mkt.constants.regions.PYF), (190, mkt.constants.regions.PNG), (35, mkt.constants.regions.PHL), (187, mkt.constants.regions.PAK), (11, mkt.constants.regions.POL), (204, mkt.constants.regions.SPM), (192, mkt.constants.regions.PCN), (194, mkt.constants.regions.PRI), (189, mkt.constants.regions.PSE), (193, mkt.constants.regions.PRT), (188, mkt.constants.regions.PLW), (191, mkt.constants.regions.PRY), (195, mkt.constants.regions.QAT), (196, mkt.constants.regions.REU), (197, mkt.constants.regions.ROU), (16, mkt.constants.regions.SRB), (36, mkt.constants.regions.RUS), (198, mkt.constants.regions.RWA), (209, mkt.constants.regions.SAU), (216, mkt.constants.regions.SLB), (210, mkt.constants.regions.SYC), (221, mkt.constants.regions.SDN), (225, mkt.constants.regions.SWE), (212, mkt.constants.regions.SGP), (200, mkt.constants.regions.SHN), (215, mkt.constants.regions.SVN), (223, mkt.constants.regions.SJM), (214, mkt.constants.regions.SVK), (211, mkt.constants.regions.SLE), (207, mkt.constants.regions.SMR), (41, mkt.constants.regions.SEN), (217, mkt.constants.regions.SOM), (222, mkt.constants.regions.SUR), (219, mkt.constants.regions.SSD), (208, mkt.constants.regions.STP), (24, mkt.constants.regions.SLV), (256, mkt.constants.regions.SXM), (227, mkt.constants.regions.SYR), (224, mkt.constants.regions.SWZ), (237, mkt.constants.regions.TCA), (95, mkt.constants.regions.TCD), (120, mkt.constants.regions.ATF), (231, mkt.constants.regions.TGO), (229, mkt.constants.regions.THA), (228, mkt.constants.regions.TJK), (232, mkt.constants.regions.TKL), (230, mkt.constants.regions.TLS), (236, mkt.constants.regions.TKM), (39, mkt.constants.regions.TUN), (233, mkt.constants.regions.TON), (235, mkt.constants.regions.TUR), (234, mkt.constants.regions.TTO), (238, mkt.constants.regions.TUV), (57, mkt.constants.regions.TWN), (44, mkt.constants.regions.TZA), (240, mkt.constants.regions.UKR), (239, mkt.constants.regions.UGA), (4, mkt.constants.regions.GBR), (257, mkt.constants.regions.UMI), (2, mkt.constants.regions.USA), (19, mkt.constants.regions.URY), (243, mkt.constants.regions.UZB), (134, mkt.constants.regions.VAT), (205, mkt.constants.regions.VCT), (10, mkt.constants.regions.VEN), (245, mkt.constants.regions.VGB), (246, mkt.constants.regions.VIR), (244, mkt.constants.regions.VNM), (47, mkt.constants.regions.VUT), (247, mkt.constants.regions.WLF), (206, mkt.constants.regions.WSM), (249, mkt.constants.regions.YEM), (167, mkt.constants.regions.MYT), (37, mkt.constants.regions.ZAF), (250, mkt.constants.regions.ZMB), (251, mkt.constants.regions.ZWE)])),
                ('image_landing_hash', models.CharField(default=None, max_length=8, null=True, blank=True)),
            ],
            options={
                'ordering': ('-id',),
                'abstract': False,
                'db_table': 'mkt_feed_shelf',
            },
            bases=(mkt.feed.models.GroupedAppsMixin, models.Model),
        ),
        migrations.CreateModel(
            name='FeedShelfMembership',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('order', models.SmallIntegerField(null=True)),
            ],
            options={
                'ordering': ('order',),
                'abstract': False,
                'db_table': 'mkt_feed_shelf_membership',
            },
            bases=(models.Model,),
        ),
    ]
