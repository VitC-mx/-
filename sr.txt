# -*- coding: utf-8 -*-
#   萌新专属
#   2026-03-03

import base64
import json
import re
import sys
from urllib.parse import quote, urlencode
from pyquery import PyQuery as pq
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):

    def init(self, extend='{}'):
        self.host = 'https://rou.video'
        print("爬虫初始化完成，host:", self.host)
        pass

    def destroy(self):
        print("爬虫销毁")
        pass

    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; M2102J2SC Build/TKQ1.221114.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/143.0.7499.3 Mobile Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://rou.video/"
    }

    def buildVods(self, its):
        vods = []
        item_list = list(its.items())
        print("buildVods 开始处理卡片，总个数:", len(item_list))

        for idx, item in enumerate(item_list):
            vod_name = ""
            vod_pic = ""
            vod_remark = ""
            vod_year = ""

            # ────────────────────────────── 标题获取优先级 ──────────────────────────────
            # 优先级1：隐藏的简体标题 div.hidden （目前网站常用此方式放简体标题）
            hidden_div = item('div.hidden')
            if hidden_div:
                hidden_text = hidden_div.text().strip()
                if hidden_text and len(hidden_text) > 5 and "Logo" not in hidden_text:
                    vod_name = hidden_text
                    print(f"  使用隐藏简体标题 (优先): {vod_name}")

            # 优先级2：img 的 alt 属性（如果有有效内容）
            if not vod_name:
                imgs = item('img')
                for img in imgs.items():
                    alt = img.attr("alt")
                    if alt and alt.strip() and "Logo" not in alt and len(alt.strip()) > 5:
                        vod_name = alt.strip()
                        src = img.attr("src") or img.attr("data-src") or ""
                        vod_pic = src if src.startswith('http') else self.host + src if src.startswith('/') else self.host + '/' + src
                        print(f"  使用 img alt 标题: {vod_name}")
                        break

            # 优先级3：h3 标题（通常是繁体）
            if not vod_name:
                h3 = item("h3")
                if h3:
                    vod_name = h3.eq(0).text().strip()
                    print(f"  使用 h3 标题（通常繁体）: {vod_name}")

            # 优先级4：a 里面的 strong / b / 直接文本 兜底
            if not vod_name:
                a_title = item("a strong, a b, a")
                if a_title:
                    title_text = a_title.text().strip()
                    if "Logo" not in title_text and len(title_text) > 5:
                        vod_name = title_text
                        print(f"  使用 a 内文本兜底: {vod_name}")

            # 标题最终过滤 - 无效就跳过这条
            if not vod_name or "Logo" in vod_name or len(vod_name.strip()) < 6:
                print(f"  跳过无效名称卡片 {idx}: {vod_name}")
                continue

            # ────────────────────────────── 视频链接 ──────────────────────────────
            a = item('a[href^="/v/"]') or item("a") or item.closest("a")
            href = a.attr("href") if a else ""
            if not href or "/v/" not in href:
                print(f"  跳过无有效链接卡片 {idx}: {vod_name}")
                continue
            full_href = href if href.startswith('http') else self.host + href if href.startswith('/') else self.host + '/' + href

            # ────────────────────────────── 封面图（如果前面没拿到） ──────────────────────────────
            if not vod_pic:
                any_img = item("img")
                src = any_img.attr("src") or any_img.attr("data-src") or ""
                vod_pic = src if src.startswith('http') else self.host + src if src.startswith('/') else self.host + '/' + src

            # ────────────────────────────── 时长（remark） ──────────────────────────────
            duration_span = item('span.bottom-2.left-2[data-slot="badge"]')
            if duration_span:
                vod_remark = duration_span.text().strip()
            else:
                text = item.text()
                match = re.search(r'(\d+小時?\d*分\d*秒?|\d+分\d*秒|\d+秒)', text)
                if match:
                    vod_remark = match.group(1)

            # ────────────────────────────── 年份/番号 ──────────────────────────────
            year_span = item('span.bottom-0.right-0[data-slot="badge"]')
            if year_span:
                vod_year = year_span.text().strip()
            else:
                text_upper = item.text().upper()
                num_match = re.search(r'([A-Z]{2,6}-[A-Z0-9]{2,10}(?:-\d)?)', text_upper)
                if num_match:
                    vod_year = num_match.group(1)

            # 清理过长字段
            if vod_year and len(vod_year) > 15:
                vod_year = vod_year.split()[0] if vod_year.split() else vod_year[:15]

            if vod_remark and len(vod_remark) > 20:
                vod_remark = vod_remark.split()[0] if vod_remark.split() else vod_remark[:10]

            vods.append({
                'vod_id': full_href,
                'vod_name': vod_name,
                'vod_pic': vod_pic,
                'vod_remarks': vod_remark,
                'vod_year': vod_year
            })

        print(f"buildVods 完成，生成了 {len(vods)} 条有效视频")
        return vods

    def homeContent(self, filter):
        home_vods = []
        print("首页不显示视频列表，list 为空")

        classes = [
            {'type_name': '推荐', 'type_id': '/home'}
        ]

        cate_str = "国产AV$國產AV#自拍流出$自拍流出#探花$探花#糖心Vlog$糖心Vlog#OnlyFans$OnlyFans#日本$日本#麻豆传媒$麻豆傳媒#蜜桃传媒$蜜桃影像傳媒#星空传媒$星空無限傳媒#天美传媒$天美傳媒#香蕉传媒$香蕉視頻傳媒#精东影业$精東影業#爱豆传媒$愛豆傳媒#麻豆系列$MD#唐伯虎$tangbo_hu#玩偶姐姐$HongKongDoll#台北娜娜$Nana_Taipei#米菲兔$BunnyMiffy#艾莉$ssrpeach#苏畅$suchanghub#91沈先生$91沈先生#探花精选$探花精選400#小宝探花$小寶尋花#小景甜$調教小景甜#午夜探花$午夜尋花#探花合集$探花合集"
        cate_list = [item.strip() for item in cate_str.split('#') if item.strip()]

        seen_tid = set()
        for item in cate_list:
            if '$' in item:
                parts = item.split('$', 1)
                name = parts[0].strip()
                tid = parts[1].strip() if len(parts) > 1 else ""
                full_tid = f"/t/{tid}"
                if name and tid and full_tid not in seen_tid:
                    classes.append({'type_name': name, 'type_id': full_tid})
                    seen_tid.add(full_tid)

        print("分类列表加载完成，共 {} 个（无重复）".format(len(classes)))

        result = {
            'class': classes,
            'list': home_vods,
            'filters': {}
        }

        print("首页最终结果 - 分类: {} 个，视频: 0 个".format(len(classes)))

        return result

    def categoryContent(self, tid, pg, filter, extend):
        params = {}
        if int(pg) > 1:
            params['page'] = str(pg)
        if extend and isinstance(extend, dict) and 'order' in extend:
            params['order'] = extend['order']

        query = urlencode(params)
        url = f"{self.host}{tid}" if tid.startswith('/') else f"{self.host}/{tid}"
        if query:
            url += "?" + query

        print(f"categoryContent 请求URL: {url} (pg={pg})")

        resp = self.fetch(url, headers=self.headers)
        doc = pq(resp.content)

        items = doc('div[data-slot="card"]')
        print(f"分类 {tid} 第{pg}页 主选择器抓到: {len(items)} 个")

        if len(items) < 5:
            items = doc('div[data-slot="card"], div.flex.flex-col.rounded-xl.border.shadow-sm.group.overflow-hidden, div.relative.group, div:has(img):has(h3)')
            print(f"分类 {tid} 第{pg}页 兜底选择器抓到: {len(items)} 个")

        vods_raw = self.buildVods(items)

        unique_vods = {}
        for vod in vods_raw:
            vid = vod['vod_id']
            if vid in unique_vods:
                continue
            year = vod.get('vod_year', '').strip()
            remark = vod.get('vod_remarks', '').strip()
            vod['vod_remarks'] = remark
            unique_vods[vid] = vod

        vods = list(unique_vods.values())

        print(f"分类 {tid} 第{pg}页 去重后视频数: {len(vods)}")

        next_link = doc(f'a[href*="page={int(pg)+1}"]')
        has_next = bool(next_link)

        if tid.startswith('/search?q='):
            pagecount = 1
            print(f"检测到标签跳转 ({tid})，强制 pagecount=1")
        elif has_next and len(vods) > 0:
            pagecount = int(pg) + 1
        else:
            pagecount = int(pg)

        result = {
            'list': vods,
            'page': int(pg),
            'pagecount': pagecount,
            'limit': len(vods) or 90,
            'total': len(vods) * pagecount
        }

        print(f"分类 {tid} 第{pg}页 最终输出: {len(vods)} 条，pagecount={pagecount}")

        return result

    def detailContent(self, ids):
        if not ids or not ids[0]:
            return {'list': []}

        url = ids[0] if ids[0].startswith('http') else f"{self.host}{ids[0]}"
        print(f"detailContent 请求详情页: {url}")

        resp = self.fetch(url, headers=self.headers)
        content = resp.text
        doc = pq(content)

        ev_match = re.search(r'"ev"\s*:\s*(\{"d":"[^"]+","k":\d+\})', content)
        if not ev_match:
            vod = {'vod_content': '暂无播放链接', 'vod_play_from': 'OK影视', 'vod_play_url': ''}
            return {'list': [vod]}

        ev_str = ev_match.group(1)
        ev = json.loads(ev_str)
        d = ev.get('d', '')
        k = ev.get('k', 0)

        play_url = ""
        try:
            raw = base64.b64decode(d)
            plain_bytes = bytes((b - k) & 255 for b in raw)
            plain_str = plain_bytes.decode('utf-8', errors='ignore')
            video_data = json.loads(plain_str)
            play_url = video_data.get('videoUrl', '')
            print("播放地址解密成功:", play_url)
        except Exception as e:
            print("解密失败:", str(e))

        tags_list = []

        # 第一步：抓主分类标签
        tags_div = doc("div.flex.flex-wrap.gap-1\\.5")
        if tags_div:
            for a_tag in tags_div("a").items():
                span = a_tag("span[data-slot=\"badge\"]")
                if span:
                    tag_text = span.text().strip()
                    tag_href = a_tag.attr("href")
                    if tag_text and tag_href and tag_href.startswith('/t/'):
                        tags_list.append(f'[a=cr:{{"id":"{tag_href}"}}/] {tag_text} [/a]')
                        print(f"  添加分类标签: {tag_text} -> {tag_href}")

        # 第二步：抓蓝色官方番号标签
        blue_div = doc("div.mb-1")
        if blue_div:
            blue_span = blue_div("span[data-slot=\"badge\"].bg-gradient-to-r.from-blue-600")
            if blue_span:
                text = blue_span.text().strip()
                if text:
                    search_path = f"/search?q={quote(text)}"
                    tag_str = f'[a=cr:{{"id":"{search_path}"}}/] {text} [/a]'
                    if tag_str not in tags_list:
                        tags_list.append(tag_str)
                        print(f"  添加蓝色官方番号标签（放最后）: {text}")

        tags_display = f'[标签]{"，".join(tags_list)}' if tags_list else '[标签]暂无标签'

        desc_div = doc("div.mt-3.pt-3.border-t.border-gray-200.dark\\:border-gray-800")
        desc_text = desc_div("p.text-sm.text-gray-600.dark\\:text-gray-400.whitespace-pre-wrap.leading-relaxed").text().strip() if desc_div else ""
        desc_part = f'[简介]{desc_text}' if desc_text else ''

        vod_content = tags_display
        if desc_part:
            vod_content += ' ' + desc_part

        vod = {
            'vod_content': vod_content or '暂无标签',
            'vod_play_from': 'Rou',
            'vod_play_url': f'萌新⭐️直链${play_url}' if play_url else '播放$暂无播放地址'
        }

        print("detailContent 生成标签完成:", tags_display)

        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        params = {'q': key}
        if int(pg) > 1:
            params['page'] = str(pg)

        url = f"{self.host}/search?{urlencode(params)}"
        print(f"搜索关键词: {key} | 页码: {pg} | 请求URL: {url}")

        search_headers = self.headers.copy()
        search_headers["Referer"] = f"{self.host}/search?q={quote(key)}"

        resp = self.fetch(url, headers=search_headers)
        print(f"第{pg}页 响应长度: {len(resp.text)} 字节")

        doc = pq(resp.content)

        items = doc('div[data-slot="card"]')
        print(f"第{pg}页 主选择器抓到: {len(items)} 个")

        if len(items) < 5:
            items = doc('div[data-slot="card"], div.flex.flex-col.rounded-xl.border.shadow-sm.group.overflow-hidden')
            print(f"第{pg}页 兜底选择器抓到: {len(items)} 个")

        vods_raw = self.buildVods(items)

        seen_ids = set()
        vods = []
        for vod in vods_raw:
            vid = vod['vod_id']
            if vid in seen_ids:
                continue
            seen_ids.add(vid)

            year = vod.get('vod_year', '').strip()
            remark = vod.get('vod_remarks', '').strip()
            if year and remark:
                vod['vod_remarks'] = f"{year}|{remark}"
            elif year:
                vod['vod_remarks'] = year
            elif remark:
                vod['vod_remarks'] = remark

            vods.append(vod)

        print(f"第{pg}页 搜索去重后视频数: {len(vods)}")

        next_link = doc(f'a[href*="page={int(pg)+1}"]')
        has_next = bool(next_link)

        if has_next and len(vods) > 0:
            pagecount = int(pg) + 1
        else:
            pagecount = int(pg)

        result = {
            'list': vods,
            'page': int(pg),
            'pagecount': pagecount,
            'limit': len(vods) or 90,
            'total': 999999 if pagecount > int(pg) else len(vods) * int(pg)
        }

        print(f"搜索 '{key}' 第{pg}页 输出视频数: {len(vods)}，pagecount 实时设为 {pagecount}")

        return result

    def playerContent(self, flag, id, vipFlags):
        return {
            'parse': 0,
            'url': id,
            'header': json.dumps(self.headers)
        }