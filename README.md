# Beyond100 engine

Code behind [beyond100tennis.com](https://beyond100tennis.com) and the Instagram accounts
[@beyond100.tennis](https://instagram.com/beyond100.tennis) and [@beyond100.padel](https://instagram.com/beyond100.padel).

- The workflows here run the hourly site update, the fast result updates and the weekly jobs.
- Data (results, rankings, photos, posts) lives in a separate private repository; the workflows read and write it
  with a scoped token. Third-party data is never stored in this repository.
- Keys are GitHub secrets and are never printed in logs.

All rights reserved. The code is public so the workflows can run, not for reuse.
