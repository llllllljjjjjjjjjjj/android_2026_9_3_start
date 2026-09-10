"use strict";
// 拿搜索结果视频列表：hook SearchMixFeedList.setJsonData(原始JSON) + getItems()
var n = 0;
var MAXOUT = 4000;

Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }

  try {
    var SML = Java.use("com.ss.android.ugc.aweme.discover.mixfeed.SearchMixFeedList");
    console.log("@@ SML found");

    SML.setJsonData.implementation = function (s) {
      try {
        var t = S(s);
        n++;
        console.log("@@MIXJSON[" + n + "] len=" + t.length);
        console.log("@@MIXTXT " + t.slice(0, MAXOUT));
      } catch (e) { console.log("@@ err " + S(e)); }
      return this.setJsonData(s);
    };
    console.log("@@ hooked setJsonData");

    SML.getItems.implementation = function () {
      var r = this.getItems();
      try {
        var sz = r ? r.size() : -1;
        console.log("@@ITEMS size=" + sz);
        if (r && sz > 0) {
          for (var i = 0; i < Math.min(sz, 3); i++) {
            var it = r.get(i);
            try { console.log("@@  item[" + i + "] cls=" + it.getClass().getName()); } catch (e2) { }
            try { console.log("@@  item[" + i + "] " + S(it.toString()).slice(0, 400)); } catch (e3) { }
          }
        }
      } catch (e) { console.log("@@ items err " + S(e)); }
      return r;
    };
    console.log("@@ hooked getItems");
  } catch (e) { console.log("@@ SML err " + S(e)); }
});
