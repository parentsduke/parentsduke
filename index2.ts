import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "authorization, content-type",
      },
    });
  }

  try {
    const body = await req.json();
    const { action, type, title, submittedBy, email, name, class: classVal, wxgroup, record_id } = body;

    // ========== 处理邀请请求 ==========
    if (action === "invite" || type === "invite_approval") {
      return await handleInviteApproval(email, name, record_id);
    }

    // ========== 处理拒绝请求 ==========
    if (action === "reject") {
      return await handleReject(body.record_id);
    }

       // ========== 处理提交失败通知 ==========
    if (type === "invite_request_failed") {
      return await handleInviteRequestFailed(body);
    }

    // ========== 原有的通知逻辑 ==========
    return await handleNotification(body);

  } catch (e) {
    console.error("Error:", e);
    return new Response(JSON.stringify({ error: e.message }), {
      status: 500,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      },
    });
  }
});

// ========== 处理邀请批准 ==========
async function handleInviteApproval(recipientEmail: string, name: string, recordId: string) {
  const RESEND_API_KEY = Deno.env.get("RESEND_API_KEY");
  const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
  const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

  if (!recipientEmail || !name || !recordId) {
    return new Response(
      JSON.stringify({ error: "Missing required fields: email, name, record_id" }),
      {
        status: 400,
        headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      }
    );
  }

  try {
    // 验证邮箱格式
    if (!isValidEmail(recipientEmail)) {
      return new Response(
        JSON.stringify({ error: "Invalid email format" }),
        {
          status: 400,
          headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
        }
      );
    }

    const adminClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

    // 1️⃣ 更新数据库状态为 approved
    const { error: updateError } = await adminClient
      .from("pending_uploads")
      .update({
        status: "approved",
        approved_at: new Date().toISOString(),
      })
      .eq("id", recordId);

    if (updateError) {
      console.error("Database update error:", updateError);
      return new Response(
        JSON.stringify({ error: "Failed to update record: " + updateError.message }),
        {
          status: 500,
          headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
        }
      );
    }

    // 2️⃣ 发送 Supabase 邀请邮件（含登录 token）
    const { error: inviteError } = await adminClient.auth.admin.inviteUserByEmail(recipientEmail, {
      data: { display_name: name },
      redirectTo: "https://dukeparents.org/set-password.html",
    });

    if (inviteError) {
      console.error("Invite error:", inviteError.message);
      // 不中断流程，继续发通知邮件
    }

    console.log(`[Invite] Supabase invite sent to ${recipientEmail}, record updated: ${recordId}`);


    return new Response(
      JSON.stringify({ success: true, user: recipientEmail }),
      {
        status: 200,
        headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      }
    );

  } catch (e) {
    console.error("handleInviteApproval error:", e);
    return new Response(
      JSON.stringify({ error: e.message }),
      {
        status: 500,
        headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      }
    );
  }
}

// ========== 生成邀请邮件 HTML ==========
function generateInviteEmailHTML(name: string, email: string): string {
  return `
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; background: #f4f4f4; padding: 20px;">
<div style="max-width: 500px; margin: 0 auto; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
<div style="background: #001a4d; padding: 28px 32px; text-align: center;">
<h1 style="color: #c9a84c; font-size: 24px; margin: 0;">Duke Parents</h1>
<p style="color: #aab4cc; font-size: 13px; margin: 6px 0 0;">扯谈群网站</p>
</div>
<div style="padding: 32px;">
<p style="font-size: 16px; color: #333;">亲爱的 <strong>${name}</strong>，</p>
<p style="font-size: 15px; color: #333; line-height: 1.6;">恭喜！您的入群申请已被批准。🎉</p>
<p style="font-size: 14px; color: #555; line-height: 1.6;">您现在可以访问 Duke Parents 扯谈群网站，享受以下功能：</p>
<ul style="font-size: 14px; color: #555; line-height: 2;">
<li>🖼 浏览和分享精美照片</li>
<li>🎬 观看精彩视频内容</li>
<li>❤️ 分享生活见闻和心得</li>
<li>❓ 参与有趣的问答讨论</li>
<li>⭐ 欣赏社区精彩分享</li>
</ul>
<p style="font-size: 14px; color: #555; line-height: 1.6;">请查收来自 <strong>noreply@dukeparents.org</strong> 的另一封邀请邮件，点击其中的链接设置密码后即可登录。如未收到请查看垃圾邮件夹。</p>
<div style="background: #f0f4f8; border-left: 4px solid #001a4d; border-radius: 6px; padding: 14px 16px; margin: 20px 0;">
<p style="margin: 0; font-size: 13px; color: #444;">📧 您的登录邮箱：<br><strong style="color: #001a4d;">${email}</strong></p>
</div>
<div style="text-align: center; margin-top: 24px;">
<a href="https://dukeparents.org" style="display: inline-block; background: #0a7c3e; color: #fff; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-size: 15px; font-weight: bold;">立即访问网站 →</a>
</div>
</div>
<div style="background: #f9f9f9; padding: 16px; text-align: center; font-size: 12px; color: #999;">
© 2024 Duke Parents | 扯谈群网站<br>此邮件由自动系统发送，请勿直接回复。
</div>
</div>
</body>
</html>
`.trim();
}

// ========== 处理申请提交失败通知 ==========
async function handleInviteRequestFailed(body: any) {
  const RESEND_API_KEY = Deno.env.get("RESEND_API_KEY");
  const { email, name, class: classVal, wxgroup } = body;

  if (!email) {
    return new Response(JSON.stringify({ error: "Missing email" }), {
      status: 400,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
    });
  }

  const time = new Date().toLocaleString("zh-CN", { timeZone: "America/New_York" });

  const html = `
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; background: #f4f4f4; padding: 20px;">
<div style="max-width: 500px; margin: 0 auto; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
<div style="background: #001a4d; padding: 28px 32px; text-align: center;">
<h1 style="color: #c9a84c; font-size: 24px; margin: 0;">Duke Parents</h1>
<p style="color: #aab4cc; font-size: 13px; margin: 6px 0 0;">扯谈群网站</p>
</div>
<div style="padding: 32px;">
<p style="font-size: 16px; color: #333;">亲爱的 <strong>${name}</strong>，</p>
<p style="font-size: 15px; color: #c0392b; line-height: 1.6;">⚠️ 您于 ${time}（美东时间）提交的入群申请未能完整记录，请您重新提交一次。</p>
<div style="background: #fff8e0; border-left: 4px solid #b8860b; border-radius: 6px; padding: 14px 16px; margin: 20px 0; font-size: 13px; color: #555; line-height: 1.8;">
<b>您提交的信息：</b><br>
届别：${classVal}<br>
微信群：${wxgroup}<br>
昵称：${name}<br>
邮箱：${email}
</div>
<p style="font-size: 14px; color: #555; line-height: 1.6;">请点击下方按钮重新提交，如多次失败请联系管理员。</p>
<div style="text-align: center; margin-top: 24px;">
<a href="https://dukeparents.org" style="display: inline-block; background: #003087; color: #fff; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-size: 15px; font-weight: bold;">重新提交申请 →</a>
</div>
</div>
<div style="background: #f9f9f9; padding: 16px; text-align: center; font-size: 12px; color: #999;">
© 2024 Duke Parents | 扯谈群网站<br>此邮件由自动系统发送，请勿直接回复。
</div>
</div>
</body>
</html>`;

  const resendResponse = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${RESEND_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: "noreply@dukeparents.org",
      to: [email],
      subject: "⚠️ 您的入群申请提交未成功，请重新提交",
      html,
    }),
  });

  const resendData = await resendResponse.json();
  return new Response(
    JSON.stringify(resendResponse.ok ? { success: true } : { error: resendData }),
    {
      status: resendResponse.ok ? 200 : 500,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
    }
  );
}

// ========== 验证邮箱 ==========
function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// ========== 原有通知逻辑 ==========
async function handleNotification(body: any) {
  const RESEND_API_KEY = Deno.env.get("RESEND_API_KEY");
  const { type, title, submittedBy, email, name, class: classVal, wxgroup } = body;

  const typeLabels: Record<string, string> = {
    "照片": "🖼 新照片待审核",
    "视频": "🎬 新视频待审核",
    "文件": "📄 新文件待审核",
    "有缘启示": "❤️ 新有缘启示待审核",
    "精彩分享": "⭐ 新精彩分享待审核",
    "Q&A": "❓ 新问题待审核",
    "invite_request": "📱 新申请登录扯谈Duke群网站",
  };

  const subject = typeLabels[type] || ("新内容待审核：" + type);
  const time = new Date().toLocaleString("zh-CN", { timeZone: "America/New_York" });

  let text: string;
  if (type === "invite_request") {
    text = `收到一条新的登录申请，请登录网站管理员面板处理。\n\n届别: ${classVal || submittedBy}\n微信群名称: ${wxgroup || "未填写"}\n微信群昵称: ${name || title}\n邮箱: ${email}\n提交时间 (ET)：${time}`;
  } else {
    text = `收到新内容待审核，请登录网站管理员面板处理。\n\n类型: ${type}\n标题: ${title}\n提交者: ${submittedBy}\n提交时间 (ET)：${time}`;
  }

  const resendResponse = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${RESEND_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: "noreply@dukeparents.org",
      to: ["weihong_j@yahoo.com",
        "lixiaobing@gmail.com"],
      subject,
      html: text.replace(/\n/g, '<br>') + '<br><br><a href="https://dukeparents.org/approve.html" style="display:inline-block;padding:10px 20px;background:#003087;color:#fff;text-decoration:none;border-radius:6px;font-size:14px;">👉 点击进入审批页面</a>',
    }),
  });

  const resendData = await resendResponse.json();

  return new Response(
    JSON.stringify(resendResponse.ok ? { success: true } : { error: resendData }),
    {
      status: resendResponse.ok ? 200 : 500,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      },
    }
  );
}

// ========== 处理拒绝 ==========
async function handleReject(recordId: string) {
  if (!recordId) {
    return new Response(
      JSON.stringify({ error: "Missing record_id" }),
      { status: 400, headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" } }
    );
  }

  const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
  const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const adminClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

  const { error } = await adminClient
    .from("pending_uploads")
    .update({ status: "rejected" })
    .eq("id", recordId);

  if (error) {
    return new Response(
      JSON.stringify({ error: "Failed to update record: " + error.message }),
      { status: 500, headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" } }
    );
  }

  return new Response(
    JSON.stringify({ success: true }),
    { status: 200, headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" } }
  );
}

// ========== 方糖微信推送 ==========
async function handleWxNotify(body: any) {
  const fangtangKey = Deno.env.get("FANGTANG_KEY");
  if (!fangtangKey) {
    return new Response(
      JSON.stringify({ error: "FANGTANG_KEY 未配置" }),
      { status: 500, headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" } }
    );
  }
  const { title, desp } = body;
  if (!title) {
    return new Response(
      JSON.stringify({ error: "缺少 title 参数" }),
      { status: 400, headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" } }
    );
  }
  const ftRes = await fetch(`https://sctapi.ftqq.com/${fangtangKey}.send`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ title, desp: desp || "" }),
  });
  const ftData = await ftRes.json();
  return new Response(
    JSON.stringify({ ok: true, fangtang: ftData }),
    { headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" } }
  );
}
