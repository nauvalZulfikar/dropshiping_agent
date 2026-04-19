export interface TikTokSession {
  access_token: string;
  refresh_token: string;
  open_id: string;
  expires_at: number;
}

export interface TikTokUser {
  open_id: string;
  union_id?: string;
  avatar_url: string;
  display_name: string;
  username: string;
}

export interface CreatorInfo {
  privacy_level_options: string[];
  comment_disabled: boolean;
  duet_disabled: boolean;
  stitch_disabled: boolean;
  max_video_post_duration_sec: number;
}

export interface PublishInitResponse {
  publish_id: string;
  upload_url: string;
}

export interface PublishStatus {
  status: "PROCESSING_UPLOAD" | "PROCESSING_DOWNLOAD" | "SEND_TO_USER_INBOX" | "PUBLISH_COMPLETE" | "FAILED";
  fail_reason?: string;
  publish_id: string;
}

export interface RecentPost {
  publish_id: string;
  caption: string;
  status: string;
  posted_at: string;
}
