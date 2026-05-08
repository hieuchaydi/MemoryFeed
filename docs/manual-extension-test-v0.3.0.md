# MemoryFeed v0.3.0 Manual Extension Test Checklist

This checklist is for real browser validation after code-level tests pass.

## Facebook

- [ ] Post text is captured.
- [ ] `author_name` is present.
- [ ] `canonical_url` is correct.
- [ ] `media_urls` exists when post has images.
- [ ] No duplicate capture when scrolling back.

## X/Twitter

- [ ] Tweet text is captured.
- [ ] `author_name` or `author_handle` is present.
- [ ] `canonical_url` removes tracking/extra query params.
- [ ] `post_id` is extracted correctly from URL.

## YouTube

- [ ] Video/community item is captured.
- [ ] `thumbnail_url` is present.
- [ ] `canonical_url` normalization is correct.
- [ ] Missing author does not hard-fail capture.

## LinkedIn

- [ ] Feed post is captured.
- [ ] `author_name` is present.
- [ ] `media_urls` exists when post has images.
- [ ] No duplicate capture when feed re-renders.

## TikTok

- [ ] Post/video is captured.
- [ ] `canonical_url` is correct.
- [ ] `thumbnail_url`/`media_urls` is present when available.
- [ ] Dwell-based capture does not spam duplicates.

## Notes

- If small bugs are found, patch them in v0.3.1.
- Avoid adding extra scope to v0.3.0 once release is stable.
