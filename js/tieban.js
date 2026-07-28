// 铁板神数核心算法 — 由 main.py 移植（纯前端，无后端依赖）
// 依赖：js/lunar.js（提供 Solar/LunarMonth 等全局）、js/db-data.js（提供 window.TIEBAN_DB）
;(function (root) {
  'use strict';

  // ---- 环境解析：浏览器取 window 全局，Node 取 global ----
  var G = (typeof window !== 'undefined') ? window
        : (typeof global !== 'undefined') ? global : root;
  function DB() { return G.TIEBAN_DB; }

  // ============================================================
  // 静态常量（对应 main.py）
  // ============================================================
  var TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"];
  var DI_ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"];

  var NAYIN_WUXING = {
    "甲子": "金", "乙丑": "金", "丙寅": "火", "丁卯": "火", "戊辰": "木", "己巳": "木",
    "庚午": "土", "辛未": "土", "壬申": "金", "癸酉": "金", "甲戌": "火", "乙亥": "火",
    "丙子": "水", "丁丑": "水", "戊寅": "土", "己卯": "土", "庚辰": "金", "辛巳": "金",
    "壬午": "木", "癸未": "木", "甲申": "水", "乙酉": "水", "丙戌": "土", "丁亥": "土",
    "戊子": "火", "己丑": "火", "庚寅": "木", "辛卯": "木", "壬辰": "水", "癸巳": "水",
    "甲午": "金", "乙未": "金", "丙申": "火", "丁酉": "火", "戊戌": "木", "己亥": "木",
    "庚子": "土", "辛丑": "土", "壬寅": "金", "癸卯": "金", "甲辰": "火", "乙巳": "火",
    "丙午": "水", "丁未": "水", "戊申": "土", "己酉": "土", "庚戌": "金", "辛亥": "金",
    "壬子": "木", "癸丑": "木", "甲寅": "水", "乙卯": "水", "丙辰": "土", "丁巳": "土",
    "戊午": "火", "己未": "火", "庚申": "木", "辛酉": "木", "壬戌": "水", "癸亥": "水"
  };

  var HOU_TIAN_GUA_NUM = {
    "坎": 1, "坤": 2, "震": 3, "巽": 4, "中": 5, "乾": 6, "兑": 7, "艮": 8, "离": 9
  };

  var KE_GAN_NUMBER = {
    "初刻": 1, "一刻": 2, "二刻": 3, "三刻": 4,
    "四刻": 5, "五刻": 6, "六刻": 7, "正刻": 8
  };

  // (初刻,一刻,...,正刻) 的分钟区间 [start,end)
  var EIGHT_KE_TIME_RANGE = [
    ["初刻", 0, 15], ["一刻", 15, 30], ["二刻", 30, 45], ["三刻", 45, 60],
    ["四刻", 60, 75], ["五刻", 75, 90], ["六刻", 90, 105], ["正刻", 105, 120]
  ];

  var TIEBAN_CORE_SECRET = 48;

  var BA_GUA_JIA_ZHE_DESC = {
    "乾": "乾卦六为头，初爻从36起",
    "兑": "兑为后少女，初爻从3起"
  };

  // ============================================================
  // 辅助函数（对应 main.py）
  // ============================================================
  function getEightKeFromTime(hour, minute) {
    var minutesInKe;
    if (hour === 23) minutesInKe = minute;
    else if (hour === 0) minutesInKe = 60 + minute;
    else minutesInKe = (hour % 2) * 60 + minute;
    for (var i = 0; i < EIGHT_KE_TIME_RANGE.length; i++) {
      var r = EIGHT_KE_TIME_RANGE[i];
      if (minutesInKe >= r[1] && minutesInKe < r[2]) return r[0];
    }
    return "正刻";
  }

  function getKeGanNumber(keName) {
    return KE_GAN_NUMBER.hasOwnProperty(keName) ? KE_GAN_NUMBER[keName] : 8;
  }

  function calculateTiebanFortune(baseNum, keGanNum) {
    return baseNum + keGanNum * TIEBAN_CORE_SECRET;
  }

  function getSanYuanPeriod(year) {
    if (year >= 1864 && year <= 1923) return "上元";
    if (year >= 1924 && year <= 1983) return "中元";
    if (year >= 1984 && year <= 2043) return "下元";
    if (year > 2043) {
      var offset = (year - 1864) % 120;
      if (offset < 60) return "上元";
      else if (offset < 120) return "中元";
    }
    return "下元";
  }

  function getWuShuJiGongGua(sanYuan, gender, isYang) {
    if (sanYuan === "上元") return gender === "男" ? "艮" : "坤";
    if (sanYuan === "中元") {
      if ((gender === "男" && isYang) || (gender === "女" && !isYang)) return "艮";
      return "坤";
    }
    if (sanYuan === "下元") return gender === "男" ? "离" : "兑";
    return "坤";
  }

  function getBaguaJiazeStart(hexName) {
    if (hexName === "乾") return 36;
    if (hexName === "兑") return 3;
    return 30;
  }

  function applyBaguaJiazeRule(currentNum, hexName, iteration) {
    iteration = iteration || 1;
    var start = getBaguaJiazeStart(hexName);
    var result = start + currentNum;
    if (result >= 10) result = result % 10;
    if (result === 6 || result === 8) return [result, true, iteration];
    if (iteration < 10) return applyBaguaJiazeRule(result, hexName, iteration + 1);
    return [result, false, iteration];
  }

  // 与 Python float() 语义对齐：可转数字即为真
  function isNumeric(value) {
    if (value === "" || value === null || value === undefined) return false;
    return !isNaN(Number(value));
  }

  function getFortuneDuanyu(fortuneNum) {
    if (fortuneNum === "" || fortuneNum === null || fortuneNum === undefined || !isNumeric(fortuneNum)) {
      return ["", ""];
    }
    var num = Math.trunc(parseFloat(fortuneNum));
    var v = DB().FORTUNE_DUANYU_MAP[String(num)];
    return v ? [v[0], v[1]] : ["未找到断语", "未知"];
  }

  function calculateCorrection(originalCorrection, age) {
    if (originalCorrection === 0) return 0;
    var nc;
    if ((age >= 1 && age <= 10) || (age >= 81 && age <= 108)) {
      nc = originalCorrection + 2;
      if (nc > 6) nc -= 6;
    } else {
      nc = originalCorrection + 3;
      if (nc > 20) nc -= 20;
    }
    return nc;
  }

  function getGanGroup(gan) {
    var idx = TIAN_GAN.indexOf(gan);
    if (idx < 0) return "甲己";
    return ["甲己", "乙庚", "丙辛", "丁壬", "戊癸"][idx % 5];
  }

  function getLiunianGroups(yearGan, yearZhi) {
    var bGroup = "未知";
    if ("寅午戌".indexOf(yearZhi) >= 0) bGroup = "寅午戌";
    else if ("申子辰".indexOf(yearZhi) >= 0) bGroup = "申子辰";
    else if ("巳酉丑".indexOf(yearZhi) >= 0) bGroup = "巳酉丑";
    else if ("亥卯未".indexOf(yearZhi) >= 0) bGroup = "亥卯未";
    var sGroup = "未知";
    if ("甲乙丙丁".indexOf(yearGan) >= 0) sGroup = "甲乙丙丁";
    else if ("戊己".indexOf(yearGan) >= 0) sGroup = "戊己";
    else if ("庚辛".indexOf(yearGan) >= 0) sGroup = "庚辛";
    else if ("壬癸".indexOf(yearGan) >= 0) sGroup = "壬癸";
    return [bGroup, sGroup];
  }

  function isYangYear(yearGan) {
    return ["甲", "丙", "戊", "庚", "壬"].indexOf(yearGan) >= 0;
  }

  // ============================================================
  // 八字转换（cnlunar → lunar.js 等价映射）
  // ============================================================
  var YEAR_DIGITS = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九"];
  var MONTH_NAMES = { 1: "正", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九", 10: "十", 11: "冬", 12: "腊" };

  function pad2(n) { return (n < 10 ? "0" : "") + n; }

  function yearToCn(y) {
    return String(y).split("").map(function (c) { return YEAR_DIGITS[Number(c)]; }).join("");
  }

  function convertToBaziInfo(y, mo, d, h, mi) {
    var solar = G.Solar.fromYmdHms(y, mo, d, h, mi, 0);
    var lu = solar.getLunar();
    var monthRaw = lu.getMonth();            // 闰月为负
    var isLeap = monthRaw < 0;
    var lunarMonth = Math.abs(monthRaw);
    var lunarDay = lu.getDay();

    // lunar_str：复刻 cnlunar 格式 "一九九零年 四月小廿一"
    var dayCount = G.LunarMonth.fromYm(lu.getYear(), monthRaw).getDayCount();
    var monthCn = (isLeap ? "闰" : "") + MONTH_NAMES[lunarMonth] + "月" + (dayCount === 30 ? "大" : "小");
    var lunarStr = yearToCn(lu.getYear()) + "年 " + monthCn + lu.getDayInChinese();

    return {
      lunar_month: lunarMonth,
      lunar_day: lunarDay,
      is_leap: isLeap,
      bazi: {
        year: lu.getYearInGanZhi(),
        month: lu.getMonthInGanZhi(),
        day: lu.getDayInGanZhiExact(),
        time: lu.getTimeInGanZhi()
      },
      date_str: y + "-" + pad2(mo) + "-" + pad2(d) + " " + pad2(h) + ":" + pad2(mi),
      lunar_str: lunarStr
    };
  }

  // ============================================================
  // 主计算（对应 TieBanCalculator.calculate）
  // ============================================================
  function calculate(payload) {
    var db = DB();
    var birth = payload.birth_info, query = payload.query_info, gender = payload.gender;
    var y_gan = birth.bazi.year[0], y_zhi = birth.bazi.year[1];
    var t_zhi = birth.bazi.time[1];
    var d_day = birth.bazi.day, t_gan = query.bazi.time[0], t_time = query.bazi.time;

    var details = {};
    details.header_info = "性别:" + gender + ", 农历:" + birth.lunar_str + "，闰月" +
      (birth.is_leap ? "是" : "否") + "，出生八字：" +
      birth.bazi.year + " " + birth.bazi.month + " " + birth.bazi.day + " " + birth.bazi.time +
      "\n求测日期：阳历：" + query.date_str + "     八字：" +
      query.bazi.year + " " + query.bazi.month + " " + query.bazi.day + " " + query.bazi.time;

    // Step 1: 先天命数
    var m_idx = birth.lunar_month + (birth.is_leap ? 1 : 0);
    var calc_month = String(m_idx);
    if (m_idx > 12) calc_month = "1";
    var month_val = db.tables["14-1"].hasOwnProperty(calc_month) ? db.tables["14-1"][calc_month] : parseInt(calc_month, 10);
    var time_val = db.tables["14-2"].hasOwnProperty(t_zhi) ? db.tables["14-2"][t_zhi] : 0;
    var cong_num = month_val + 3 - time_val;
    if (cong_num <= 0) cong_num += 12;
    details.cong_calc = "先天命数 = " + cong_num;
    details.cong_num = cong_num;

    // Step 2: 五音命数
    var gan_group = getGanGroup(y_gan);
    var t14_3 = db.tables["14-3"] || {};
    var congRow = t14_3[String(cong_num)] || {};
    var tone = congRow.hasOwnProperty(gan_group) ? congRow[gan_group] : "宫";
    var tone_num = db.tables["14-4"].hasOwnProperty(tone) ? db.tables["14-4"][tone] : 5;
    details.tone_num = tone_num;

    // Step 3: 日命数与时运数
    var day_n = NAYIN_WUXING.hasOwnProperty(d_day) ? NAYIN_WUXING[d_day] : "金";
    var t14_5 = db.tables["14-5"] || {};
    var dayRow = t14_5[day_n] || {};
    var day_life = dayRow.hasOwnProperty(t_gan) ? dayRow[t_gan] : 0;
    var time_n = NAYIN_WUXING.hasOwnProperty(t_time) ? NAYIN_WUXING[t_time] : "金";
    var time_luck = db.tables["14-6"].hasOwnProperty(time_n) ? db.tables["14-6"][time_n] : 0;
    details.day_life_calc = "日命:" + day_life + ", 时运:" + time_luck;

    // Step 4: 刻别（八刻细分）
    // birth date_str 形如 "YYYY-MM-DD HH:MM"
    var dp = birth.date_str.split(" ");
    var tp = dp[1].split(":");
    var b_hour = parseInt(tp[0], 10), b_minute = parseInt(tp[1], 10);
    var moment_cn = getEightKeFromTime(b_hour, b_minute);
    var ke_gan_num = getKeGanNumber(moment_cn);

    var sum_val = day_life + time_luck;
    var is_yang = isYangYear(y_gan);
    var grp = ((gender === "男" && is_yang) || (gender === "女" && !is_yang)) ? "阳男阴女" : "阴男阳女";
    var cond = sum_val > 6 ? ">6" : "<=6";

    var moment = "Main";
    for (var ri = 0; ri < db.rule_tables.length; ri++) {
      var r = db.rule_tables[ri];
      if (r["组别"] === grp && r["和值条件"] === cond) {
        moment = (r["刻别"] === "初刻") ? "Initial" : "Main";
        break;
      }
    }
    details.moment_calc = "考刻: " + moment_cn + " (刻干数:" + ke_gan_num + ", " + grp + ")";
    details.moment_cn = moment_cn;
    details.ke_gan_num = ke_gan_num;

    // Step 5: 本命数与终局条文数
    var base_val = tone_num * 5 + day_life + time_luck;
    var fact = (sum_val <= 6) ? (base_val - 1) : (base_val - 6);
    var main_num = fact * 30 + birth.lunar_day;
    var final_fortune_num = calculateTiebanFortune(main_num, ke_gan_num);
    details.main_calc = "本命数: " + main_num + ", 终局条文数: " + final_fortune_num +
      " (公式:" + main_num + "+" + ke_gan_num + "×48)";
    details.main_num = main_num;
    details.final_fortune_num = final_fortune_num;

    // Step 6: 卦名
    var hex_name = db.HEXAGRAM_DETAIL_MAP[moment_cn + "|" + main_num];
    if (hex_name === undefined) hex_name = db.HEXAGRAM_MAP[String(main_num)];
    if (hex_name === undefined) hex_name = "未知(刻别:" + moment_cn + ",本命数:" + main_num + "未匹配)";
    details.hex_name = hex_name;

    var tbl_data = db.DESTINY_DATA[hex_name + "|" + moment + "|" + cong_num];
    if (tbl_data === undefined) tbl_data = null;
    if (tbl_data && tbl_data.offsets) {
      var withDy = {};
      for (var k in tbl_data) if (tbl_data.hasOwnProperty(k)) withDy[k] = tbl_data[k];
      withDy.duanyus = {};
      for (var category in tbl_data.offsets) {
        if (!tbl_data.offsets.hasOwnProperty(category)) continue;
        withDy.duanyus[category] = [];
        var offs = tbl_data.offsets[category];
        for (var oi = 0; oi < offs.length; oi++) {
          var fortune = tbl_data.base + tbl_data.seq + offs[oi];
          var dyr = getFortuneDuanyu(fortune);
          withDy.duanyus[category].push({ fortune: fortune, duanyu: dyr[0], age: dyr[1] });
        }
      }
      details.tbl_data = withDy;
    } else {
      details.tbl_data = tbl_data;
    }

    // Step 7: 后天命数
    var pn_sum = cong_num + main_num;
    var pn_num = pn_sum % 8;
    if (pn_num === 0) pn_num = 8;

    var birth_year = parseInt(birth.date_str.split("-")[0], 10);
    var san_yuan = getSanYuanPeriod(birth_year);
    details.san_yuan = san_yuan;

    var original_pn_num = pn_num;
    if (pn_num === 5) {
      var wu_shu_gong_gua = getWuShuJiGongGua(san_yuan, gender, is_yang);
      pn_num = HOU_TIAN_GUA_NUM.hasOwnProperty(wu_shu_gong_gua) ? HOU_TIAN_GUA_NUM[wu_shu_gong_gua] : 5;
      details.wu_shu_ji_gong = {
        original: 5,
        "寄宫卦": wu_shu_gong_gua,
        "实际命数": pn_num,
        "依据": san_yuan + " " + gender + " " + (is_yang ? "阳" : "阴")
      };
    } else {
      details.wu_shu_ji_gong = null;
    }
    details.pn_log = "先天命数＋本命数＝" + cong_num + "＋" + main_num + "＝" + pn_sum + "÷8→余数＝" + original_pn_num;
    details.pn_num = pn_num;

    var jiaze_start = getBaguaJiazeStart(hex_name);
    details.bagua_jiaze = {
      "卦名": hex_name,
      "起始数": jiaze_start,
      "规则": BA_GUA_JIA_ZHE_DESC.hasOwnProperty(hex_name) ? BA_GUA_JIA_ZHE_DESC[hex_name] : "其他卦从30起"
    };

    // Step 8: 流年条文（1-108岁）
    var liunian = [];
    try {
      var lg = getLiunianGroups(y_gan, y_zhi);
      var bg = lg[0], sg = lg[1];
      var start = 0;
      var startKeys = [cong_num + "|" + bg + "|" + gender, "generic|" + bg + "|" + gender];
      for (var si = 0; si < startKeys.length; si++) {
        if (db.LIUNIAN_START.hasOwnProperty(startKeys[si])) { start = db.LIUNIAN_START[startKeys[si]]; break; }
      }
      var raw_seq = [];
      var final_seq = []; for (var fi = 0; fi < 12; fi++) final_seq.push("?");
      if (start !== 0) {
        var seqKeys = [cong_num + "|" + y_gan, cong_num + "|" + sg];
        for (var sk = 0; sk < seqKeys.length; sk++) {
          if (db.LIUNIAN_SEQ.hasOwnProperty(seqKeys[sk])) { raw_seq = db.LIUNIAN_SEQ[seqKeys[sk]]; break; }
        }
        if (raw_seq && raw_seq.length >= 12) {
          var off = (13 - start) % 12;
          final_seq = [];
          for (var i = 0; i < 12; i++) final_seq.push(raw_seq[(i + off) % 12]);
        }
      }

      var st_tg = TIAN_GAN.indexOf(y_gan);
      var st_dz = DI_ZHI.indexOf(y_zhi);

      for (var age = 1; age <= 108; age++) {
        var cur_tg = TIAN_GAN[(st_tg + age - 1) % 10];
        var cur_dz = DI_ZHI[(st_dz + age - 1) % 12];
        var sound = (final_seq[0] !== "?") ? final_seq[(age - 1) % 12] : "?";
        var mrow = db.MARKER_TABLE[cur_dz] || {};
        var marker = mrow.hasOwnProperty(String(pn_num)) ? mrow[String(pn_num)] : "?";

        var age_parity = (age % 2 !== 0) ? "奇数" : "偶数";
        var legacy_moment = (ke_gan_num <= 4) ? "初刻" : "正刻";
        var letterKey = legacy_moment + "|" + age_parity + "|" + sound + "|" + marker;
        var letter = db.LETTER_TABLE.hasOwnProperty(letterKey) ? db.LETTER_TABLE[letterKey] : "?";

        var base = 0, add = 0;
        var original_correction = 0, corrected_correction = 0;
        var original_fortune = "", corrected_fortune = "";
        var formula = "", corrected_letter = "";

        if (letter !== "?" && db.DATA_BY_LETTER.hasOwnProperty(letter + "|" + age)) {
          var dbl = db.DATA_BY_LETTER[letter + "|" + age];
          base = dbl[0]; add = dbl[1]; original_correction = dbl[2];
          formula = base + "+" + add;
          original_fortune = String(base + add);

          corrected_correction = calculateCorrection(original_correction, age);
          if (corrected_correction > 0 && db.DATA_BY_CORRECTION.hasOwnProperty(corrected_correction + "|" + age)) {
            var dbc = db.DATA_BY_CORRECTION[corrected_correction + "|" + age];
            corrected_fortune = String(dbc[0] + dbc[1]);
            corrected_letter = db.CORRECTION_TO_LETTER.hasOwnProperty(corrected_correction + "|" + age)
              ? db.CORRECTION_TO_LETTER[corrected_correction + "|" + age] : "?";
          }
        }

        var tieban_fortune = "", tieban_duanyu = "", tieban_duanyu_age = "";
        if (original_fortune && original_fortune !== "?") {
          var orig_num = parseInt(original_fortune, 10);
          if (!isNaN(orig_num)) {
            var tieban_num = calculateTiebanFortune(orig_num, ke_gan_num);
            tieban_fortune = String(tieban_num);
            var tdy = getFortuneDuanyu(tieban_fortune);
            tieban_duanyu = tdy[0]; tieban_duanyu_age = tdy[1];
          }
        }

        var ody = getFortuneDuanyu(original_fortune);
        var original_duanyu = ody[0], original_duanyu_age = ody[1];
        var cdy = getFortuneDuanyu(corrected_fortune);
        var corrected_duanyu = cdy[0], corrected_duanyu_age = cdy[1];

        var jiaze_result = "", jiaze_stop = false;
        if (corrected_fortune && corrected_fortune !== "?") {
          var fortune_val = parseInt(corrected_fortune, 10);
          if (!isNaN(fortune_val)) {
            var jr = applyBaguaJiazeRule(fortune_val, hex_name);
            jiaze_result = String(jr[0]); jiaze_stop = jr[1];
          } else {
            jiaze_result = "?";
          }
        } else {
          jiaze_result = "?";
        }

        liunian.push({
          age: age,
          year: cur_tg + cur_dz,
          sound: sound,
          marker: marker,
          letter: letter,
          corrected_letter: corrected_letter,
          original_correction: String(original_correction),
          corrected_correction: String(corrected_correction),
          formula: formula,
          original_fortune: original_fortune,
          corrected_fortune: corrected_fortune,
          tieban_fortune: tieban_fortune,
          tieban_duanyu: tieban_duanyu,
          tieban_duanyu_age: tieban_duanyu_age,
          original_duanyu: original_duanyu,
          original_duanyu_age: original_duanyu_age,
          corrected_duanyu: corrected_duanyu,
          corrected_duanyu_age: corrected_duanyu_age,
          jiaze_result: jiaze_result,
          jiaze_stop: jiaze_stop
        });
      }
    } catch (e) {
      if (typeof console !== "undefined") console.error("计算流年数据时出错:", e);
    }
    details.liunian = liunian;

    return details;
  }

  // ============================================================
  // 顶层入口：接收 index.html 的 formData，返回与旧后端一致的响应
  // ============================================================
  function calculateTieban(formData) {
    try {
      var gender = formData.gender || "男";
      var b = formData.birth || {};
      var q = formData.query || {};
      var now = new Date();
      var info_b = convertToBaziInfo(
        parseInt(b.year, 10) || 1990, parseInt(b.month, 10) || 1, parseInt(b.day, 10) || 1,
        (b.hour != null ? parseInt(b.hour, 10) : 12), (b.minute != null ? parseInt(b.minute, 10) : 0)
      );
      var info_q = convertToBaziInfo(
        parseInt(q.year, 10) || now.getFullYear(), parseInt(q.month, 10) || (now.getMonth() + 1),
        parseInt(q.day, 10) || now.getDate(),
        (q.hour != null ? parseInt(q.hour, 10) : now.getHours()),
        (q.minute != null ? parseInt(q.minute, 10) : now.getMinutes())
      );
      var result = calculate({ birth_info: info_b, query_info: info_q, gender: gender, six_qin_info: formData.six_qin_info || {} });
      return { success: true, info_b: info_b, info_q: info_q, gender: gender, result: result };
    } catch (e) {
      if (typeof console !== "undefined") console.error("排盘失败:", e);
      return { success: false, error: (e && e.message) ? e.message : String(e) };
    }
  }

  var api = {
    convertToBaziInfo: convertToBaziInfo,
    calculate: calculate,
    calculateTieban: calculateTieban
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  G.TieBan = api;
  G.calculateTieban = calculateTieban;
})(this);
