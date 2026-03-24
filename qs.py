# -*- coding: utf-8 -*-
#   萌新专属
#   2026-03-20

import json
import re
import sys
import urllib.parse
from pyquery import PyQuery as pq
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend='{}'):
        self.host = None
        # 严格精简 Header，仅保留关键三项，确保过防火墙
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; M2102J2SC Build/TKQ1.221114.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/143.0.7499.3 Mobile Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": ""
        }
        # 全局缓存实时域名，减少网络往返延迟
        self.host = self.getHost()

    def getHost(self):
        if self.host: return self.host
        # 初始引导地址
        initial_url = "https://c1d2e3f4.qisegu13.cc"
        try:
            # 捕获 302 跳转获取真实 host
            resp = self.fetch(initial_url, headers=self.headers, allow_redirects=False, timeout=5)
            target = resp.headers.get('Location', '')
            match = re.search(r'(https?://[^/]+)', target)
            if match:
                new_host = match.group(1).rstrip('/')
                self.headers['Referer'] = new_host + "/"
                return new_host
        except: pass
        # 兜底方案
        default_host = "https://u3v4w5x6.qisegu33.cc"
        self.headers['Referer'] = default_host + "/"
        return default_host

    def buildVods(self, items):
        vods = []
        for item in items.items():
            a = item("a.video-pic")
            if not a: continue
            
            # 细节：优先提取 title 属性，这是最完整的标题
            href = a.attr("href") # 示例: /voddetail/703906.html
            name = a.attr("title") or item(".title h5 a").text().strip()
            
            # 细节：图片懒加载处理
            img = item("img.lazy")
            pic = img.attr("data-original") or img.attr("src") or ""
            if pic and pic.startswith('/'): pic = self.host + pic
            
            remark = item("span.note").text().strip()
            
            # 【抠细节】复合 ID 技术：将路径、标题、图片打包传给详情页
            # 解决点击播放时标题变“立即播放”的问题，且无需再次请求详情页
            composite_id = f"{href}###{name}###{pic}"
            
            vods.append({
                'vod_id': composite_id,
                'vod_name': name,
                'vod_pic': pic,
                'vod_remarks': remark
            })
        return vods

    def homeContent(self, filter):
        # 仅保留指定分类，首页不加载数据以提高冷启动速度
        classes = [
            {'type_name': '国产', 'type_id': '169'},
            {'type_name': '日本', 'type_id': '184'},
            {'type_name': '动漫', 'type_id': '188'}
        ]
        return {'class': classes, 'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        url = f"{self.host}/vodtype/{tid}-{pg}.html"
        resp = self.fetch(url, headers=self.headers)
        doc = pq(resp.text)
        vods = self.buildVods(doc("li.content-item"))
        
        # 细节：智能翻页控制
        pagecount = int(pg)
        if len(vods) > 0 and doc("a.pagelink_a:contains('下一页')"):
            pagecount = int(pg) + 1
            
        return {'list': vods, 'page': int(pg), 'pagecount': pagecount, 'limit': len(vods), 'total': 999999}

    def detailContent(self, ids):
        # 【抠细节】零请求处理：直接从复合 ID 中解析标题和图片
        try:
            parts = ids[0].split('###')
            path = parts[0]  # 原 vod_id
            name = parts[1]  # 分类页的真实标题
            pic = parts[2]   # 分类页的封面图
            
            # 路径规律转换: /voddetail/703890.html -> /vodplay/703890-1-1.html
            play_path = path.replace('/voddetail/', '/vodplay/').replace('.html', '-1-1.html')
            play_url = self.host + play_path

            vod = {
                'vod_id': ids[0],
                'vod_name': name, # 标题百分之百与分类页一致
                'vod_pic': pic,
                'vod_play_from': '七色谷',
                'vod_play_url': f"萌新⭐️直链${play_url}"
            }
            return {'list': [vod]}
        except:
            return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        encoded_key = urllib.parse.quote(key)
        # 搜索页路由优化：第一页与后续页 URL 结构完全不同
        if str(pg) == "1":
            url = f"{self.host}/vodsearch/-------------.html?wd={encoded_key}"
        else:
            url = f"{self.host}/vodsearch/{encoded_key}----------{pg}---.html"
            
        resp = self.fetch(url, headers=self.headers)
        doc = pq(resp.text)
        vods = self.buildVods(doc("li.content-item"))
        
        pagecount = int(pg)
        if len(vods) > 0 and doc("a.pagelink_a:contains('下一页')"):
            pagecount = int(pg) + 1
            
        return {'list': vods, 'page': int(pg), 'pagecount': pagecount, 'limit': len(vods), 'total': 999999}

    def playerContent(self, flag, id, vipFlags):
        # id 为拼装好的完整播放页 URL
        try:
            resp = self.fetch(id, headers=self.headers, timeout=10)
            text = resp.text
        except:
            return {'parse': 1, 'url': id, 'header': json.dumps(self.headers)}

        real_url = ""
        # 核心解密：提取 player_aaaa 变量并进行多重解码
        script_match = re.search(r'var\s+player_aaaa\s*=\s*(\{[\s\S]*?\})\s*(?:;|</script>)', text, re.DOTALL | re.IGNORECASE)
        if script_match:
            try:
                player_str = script_match.group(1)
                url_match = re.search(r'\"url\"\s*:\s*\"([^\"]+)\"', player_str)
                if url_match:
                    encoded_url = url_match.group(1)
                    # 1. URL解码
                    real_url = urllib.parse.unquote(encoded_url)
                    # 2. Unicode 转义处理 (防止 \/ 导致播放失败)
                    if '\\' in real_url:
                        real_url = real_url.encode('utf-8').decode('unicode-escape')
            except: pass

        # 判定播放模式：m3u8 直连则 parse=0，否则丢给嗅探解析
        if real_url and real_url.startswith('http') and '.m3u8' in real_url.lower():
            parse_mode = 0
        else:
            real_url = id 
            parse_mode = 1

        return {
            'parse': parse_mode,
            'url': real_url,
            'header': json.dumps(self.headers, ensure_ascii=False)
        }

    def destroy(self):
        pass