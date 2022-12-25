pub mod irc;
pub mod matrix;

fn normalize(text: &str) -> Vec<String> {
    text.replace('　', "  ")
        .replace('，', ", ")
        .replace('。', ". ")
        .replace('！', "! ")
        .replace('？', "? ")
        .replace('：', ": ")
        .replace('；', "; ")
        .replace('（', " (")
        .replace('）', ") ")
        .lines()
        .filter_map(|line| {
            let vec = line.split_whitespace().collect::<Vec<_>>();

            if vec.is_empty() {
                None
            } else {
                Some(vec.join(" "))
            }
        })
        .collect()
}

struct LineBreaker<'a> {
    position: usize,
    limit: usize,
    line: &'a str,
}

impl<'a> LineBreaker<'a> {
    const STARTING: &'static str = "、。〃〆〕〗〞﹚﹜！＂％＇），．：；？！］｝～\
                                    ｝〕〉》」』】〙〗〟｠\
                                    ヽヾーァィゥェォッャュョヮヵヶぁぃぅぇぉっゃゅょゎゕゖㇰㇱㇲㇳㇴㇵㇶㇷㇸㇹㇺㇻㇼㇽㇾㇿ々〻\
                                    ゠〜・、。\
                                    )]}>";
    const ENDING: &'static str = "〈《「『【〔〖〝﹙﹛＄（．［｛￡￥\
                                  ｛〔〈《「『【〘〖〝｟\
                                  abcdefghijklmnopqrstuvwxyz\
                                  ABCDEFGHIJKLMNOPQRSTUVWXYZ\
                                  ([{<\
                                  0123456789";

    pub fn new(limit: usize, line: &'a str) -> Self {
        // NOTE limit must allow at least one utf8 character
        assert!(limit >= 4);

        Self {
            position: 0,
            limit,
            line,
        }
    }
}

impl<'a> Iterator for LineBreaker<'a> {
    type Item = &'a str;

    fn next(&mut self) -> Option<Self::Item> {
        if self.position > self.line.len() {
            return None;
        }

        let line = &self.line[self.position..];

        match line.char_indices().find(|&(i, _)| i > self.limit) {
            Some((index, _)) => {
                // line candidate that is at most one character over the limit
                let line = &line[..index];

                // breaking position
                // NOTE position is larger than zero if the limit is set properly
                let mut position = line.char_indices().next_back().unwrap().0;

                // typography
                if let std::ops::ControlFlow::Break(i) = line
                    .char_indices()
                    .rev()
                    // according to arXiv:1208.6109, the average word length is about 5
                    // for poisson distribution, 5 \sigma is [0, 30]
                    // thus we backtrack at most 30 characters
                    .take(31)
                    .try_fold((index, false), |(pos, flag), (i, c)| {
                        // ending character of the current line
                        if flag && !LineBreaker::ENDING.contains(c) {
                            std::ops::ControlFlow::Break(pos)
                        } else {
                            // starting character of the next line
                            std::ops::ControlFlow::Continue((i, !LineBreaker::STARTING.contains(c)))
                        }
                    })
                {
                    position = i;
                }

                self.position += position;
                Some(&line[..position])
            }
            None => {
                self.position = self.line.len() + 1;
                Some(line)
            }
        }
    }
}
