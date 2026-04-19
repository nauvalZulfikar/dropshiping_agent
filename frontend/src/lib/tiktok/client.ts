const TIKTOK_API = "https://open.tiktokapis.com/v2";

export async function exchangeCodeForToken(code: string) {
  const res = await fetch(`${TIKTOK_API}/oauth/token/`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_key: process.env.TIKTOK_CLIENT_KEY!,
      client_secret: process.env.TIKTOK_CLIENT_SECRET!,
      code,
      grant_type: "authorization_code",
      redirect_uri: process.env.TIKTOK_REDIRECT_URI!,
    }),
  });
  return res.json();
}

export async function fetchUserInfo(accessToken: string) {
  const res = await fetch(
    `${TIKTOK_API}/user/info/?fields=open_id,union_id,avatar_url,display_name,username`,
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
  return res.json();
}

export async function queryCreatorInfo(accessToken: string) {
  const res = await fetch(`${TIKTOK_API}/post/publish/creator_info/query/`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
  });
  return res.json();
}

export async function initVideoPublish(
  accessToken: string,
  opts: {
    title: string;
    privacy_level: string;
    disable_comment: boolean;
    disable_duet: boolean;
    disable_stitch: boolean;
    video_size: number;
  },
) {
  const chunkSize = opts.video_size;
  const res = await fetch(`${TIKTOK_API}/post/publish/video/init/`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      post_info: {
        title: opts.title,
        privacy_level: opts.privacy_level,
        disable_duet: opts.disable_duet,
        disable_comment: opts.disable_comment,
        disable_stitch: opts.disable_stitch,
        video_cover_timestamp_ms: 1000,
      },
      source_info: {
        source: "FILE_UPLOAD",
        video_size: opts.video_size,
        chunk_size: chunkSize,
        total_chunk_count: 1,
      },
    }),
  });
  return res.json();
}

export async function uploadVideoToTikTok(
  uploadUrl: string,
  videoBuffer: Buffer,
  contentType: string,
) {
  const size = videoBuffer.length;
  const res = await fetch(uploadUrl, {
    method: "PUT",
    headers: {
      "Content-Range": `bytes 0-${size - 1}/${size}`,
      "Content-Type": contentType || "video/mp4",
    },
    body: new Uint8Array(videoBuffer),
  });
  return { status: res.status, ok: res.ok };
}

export async function fetchPublishStatus(accessToken: string, publishId: string) {
  const res = await fetch(`${TIKTOK_API}/post/publish/status/fetch/`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ publish_id: publishId }),
  });
  return res.json();
}
