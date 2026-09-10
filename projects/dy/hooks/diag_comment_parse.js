"use strict";
// 定位评论数据的解析入口：hook CommentItemList.getServerCommentData() + 打印调用栈
Java.perform(function () {
  function S(x) { try { return x === null ? "null" : String(x); } catch (e) { return "<err>"; } }

  function stack() {
    try {
      var Log = Java.use("android.util.Log");
      var Throwable = Java.use("java.lang.Throwable");
      return Log.getStackTraceString(Throwable.$new());
    } catch (e) { return "<no stack>"; }
  }

  var n = 0;
  try {
    var CIL = Java.use("com.ss.android.ugc.aweme.comment.model.CommentItemList");
    CIL.getServerCommentData.implementation = function () {
      var v = this.getServerCommentData();
      if (n < 2) {
        n++;
        console.log("@@GSCD[" + n + "] len=" + (v ? String(v).length : -1));
        console.log("@@GSCD_VALUE " + JSON.stringify(String(v).slice(0, 200)));
        console.log("@@GSCD_STACK " + stack().split("\n").slice(0, 18).join(" | "));
      }
      return v;
    };
    console.log("@@ hooked getServerCommentData");
  } catch (e) { console.log("@@ CIL err " + S(e)); }

  // 同时看 CommentItemList 的 items 是否被 setter 填充
  try {
    var CIL2 = Java.use("com.ss.android.ugc.aweme.comment.model.CommentItemList");
    var ms = CIL2.class.getDeclaredMethods();
    var names = [];
    for (var i = 0; i < ms.length; i++) {
      var nm = ms[i].getName();
      if (/[Ss]erverComment|[Ii]tems|[Ss]etData|[Pp]arse/.test(nm)) names.push(nm);
    }
    console.log("@@CIL_METHODS " + names.join(","));
  } catch (e) { }

  rpc.exports = { reset: function () { n = 0; return 1; } };
});
