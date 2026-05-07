# Git Remote Maintenance

The NeoDev repository is maintained on both GitHub and GitLab.

- GitHub remote: `origin`
- GitHub URL: `https://github.com/XuJiachengZust/NeoDev.git`
- GitLab remote: `gitlab`
- GitLab URL: `http://gitlab.info.dbappsecurity.com.cn/jiacheng.xu3/neodev`
- Main working branch for current NeoDev SP work: `neodev-sp`

After a local commit that should be shared, push the same branch to both remotes:

```bash
git push origin neodev-sp
git push gitlab neodev-sp
```

Check remote state before changing remote configuration:

```bash
git remote -v
git branch -vv
```

Do not use `git push --mirror` unless explicitly requested; it can overwrite refs on both remotes.
