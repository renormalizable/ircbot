use anyhow::Context as _;
use async_trait::async_trait;
use pest_derive::Parser;
use serde::{Deserialize, Serialize};
use std::borrow::Cow;

use super::*;

pub use geordi::Geordi;
pub use go::Go;
pub use repl_python::ReplPython;
pub use repl_rust::ReplRust;
pub use rust::Rust;
pub use wandbox::Wandbox;

mod wandbox {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r#"
        input = _{ ^"wand" ~ ":" ~ lang ~ (WHITE_SPACE+ ~ argument ~ WHITE_SPACE+ ~ "--")? ~ WHITE_SPACE+ ~ code }
        lang = { (!WHITE_SPACE ~ ANY)+ }
        argument = { (!(WHITE_SPACE+ ~ "--" ~ WHITE_SPACE) ~ ANY)+ }
        code = { ANY* }
        opts = { "" }
    "#]
    pub struct Wandbox;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for Wandbox {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let mut request = Request {
                code: parameter.get(&Rule::code).unwrap(),
                ..Request::new(&parameter.get(&Rule::lang).unwrap().to_lowercase())?
            };
            if let Some(argument) = parameter.get(&Rule::argument) {
                request.compiler_option_raw = argument
            };
            if let Some(options) = parameter.get(&Rule::opts) {
                request.options = options
            };

            let text = reqwest::Client::new()
                .post("https://wandbox.org/api/compile.ndjson")
                .json(&request)
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;

            //info!("wandbox: {text}");

            let (out, err) = text.lines().try_fold(
                (Vec::new(), Vec::new()),
                |(mut out, mut err), line| -> Result<_, Error> {
                    let response =
                        serde_json::from_str(line).context(format!("json error: {line}"))?;

                    match response {
                        Response {
                            data,
                            r#type: "StdOut",
                        } => out.push(data),
                        Response {
                            data,
                            r#type: "StdErr" | "CompilerMessageE",
                        } => err.push(data),
                        _ => (),
                    };

                    Ok((out, err))
                },
            )?;

            if err.is_empty() {
                if out.is_empty() {
                    context.send_fmt("no output").await
                } else {
                    context.send_fmt(out.join("")).await
                }
            } else {
                context
                    .send_fmt([
                        MessageText {
                            color: (Some(Color::Red), None),
                            text: "error:".into(),
                            ..Default::default()
                        },
                        " ".into(),
                        err.join("").trim().into(),
                    ])
                    .await?;

                if !out.is_empty() {
                    context.send_fmt(out.join("")).await?;
                }

                Ok(())
            }
        }
    }

    #[allow(dead_code)]
    #[derive(Debug, Default, Serialize)]
    struct Request<'a> {
        code: &'a str,
        codes: Vec<&'a str>,
        compiler: &'a str,
        #[serde(rename = "compiler-option-raw")]
        compiler_option_raw: &'a str,
        description: &'a str,
        options: &'a str,
        #[serde(rename = "runtime-option-raw")]
        runtime_option_raw: &'a str,
        stdin: &'a str,
        title: &'a str,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Response<'a> {
        // sometimes data need to be owned
        #[serde(borrow)]
        data: Cow<'a, str>,
        r#type: &'a str,
    }

    impl<'a> Request<'a> {
        pub fn new(language: &str) -> Result<Self, Error> {
            let request = match language {
                "bash" | "shell" | "sh" => Self {
                    compiler: "bash",
                    ..Default::default()
                },
                "gcc-head-c" | "gcc-c" | "c" => Self {
                    compiler: "gcc-head-c",
                    options: "warning,gnu11,cpp-no-pedantic",
                    ..Default::default()
                },
                "clang-head-c" | "clang-c" => Self {
                    compiler: "clang-head-c",
                    options: "warning,gnu11,cpp-no-pedantic",
                    ..Default::default()
                },
                // c#
                "mono-6.12.0.122" | "mono" | "c#" | "csharp" | "cs" => Self {
                    compiler: "mono-6.12.0.122",
                    ..Default::default()
                },
                "gcc-head" | "gcc" | "c++" | "cpp" | "cxx" => Self {
                    compiler: "gcc-head",
                    options: "warning,boost-nothing-gcc-head,gnu++2b,cpp-no-pedantic",
                    ..Default::default()
                },
                "clang-head" | "clang" => Self {
                    compiler: "clang-head",
                    options: "warning,boost-nothing-clang-head,gnu++2b,cpp-no-pedantic",
                    ..Default::default()
                },
                "gcc-head-pp" | "gcc-pp" => Self {
                    compiler: "gcc-head-pp",
                    options: "cpp-p,boost-nothing-gcc-head-header",
                    ..Default::default()
                },
                "clang-head-pp" | "clang-pp" => Self {
                    compiler: "clang-head-pp",
                    options: "cpp-p,boost-nothing-clang-head-header",
                    ..Default::default()
                },
                "crystal-1.0.0" | "crystal" | "cr" => Self {
                    compiler: "crystal-1.0.0",
                    ..Default::default()
                },
                // d
                "dmd-2.096.0" | "dmd" | "d" => Self {
                    compiler: "dmd-2.096.0",
                    ..Default::default()
                },
                "elixir-1.11.4" | "elixir" | "exs" => Self {
                    compiler: "elixir-1.11.4",
                    ..Default::default()
                },
                "erlang-23.3.1" | "erlang" | "erl" => Self {
                    compiler: "erlang-23.3.1",
                    ..Default::default()
                },
                "go-1.16.3" | "go" => Self {
                    compiler: "go-1.16.3",
                    ..Default::default()
                },
                "groovy-3.0.8" | "groovy" => Self {
                    compiler: "groovy-3.0.8",
                    ..Default::default()
                },
                "ghc-9.0.1" | "ghc" | "haskell" | "hs" => Self {
                    compiler: "ghc-9.0.1",
                    options: "haskell-warning",
                    ..Default::default()
                },
                "openjdk-jdk-15.0.3+2" | "openjdk" | "java" => Self {
                    compiler: "openjdk-jdk-15.0.3+2",
                    ..Default::default()
                },
                // javascript
                "nodejs-16.14.0" | "nodejs" | "javascript" | "js" => Self {
                    compiler: "nodejs-16.14.0",
                    ..Default::default()
                },
                "julia-1.6.1" | "julia" | "jl" => Self {
                    compiler: "julia-1.6.1",
                    ..Default::default()
                },
                "lazyk" => Self {
                    compiler: "lazyk",
                    ..Default::default()
                },
                // lisp
                "clisp-2.49" | "clisp" | "lisp" => Self {
                    compiler: "clisp-2.49",
                    ..Default::default()
                },
                // lua
                "lua-5.4.3" | "lua" => Self {
                    compiler: "lua-5.4.3",
                    ..Default::default()
                },
                "nim-1.6.6" | "nim" => Self {
                    compiler: "nim-1.6.6",
                    ..Default::default()
                },
                "ocaml-4.12.0" | "ocaml" | "ml" => Self {
                    compiler: "ocaml-4.12.0",
                    ..Default::default()
                },
                "openssl-1.1.1k" | "openssl" => Self {
                    compiler: "openssl-1.1.1k",
                    ..Default::default()
                },
                "php-8.0.3" | "php" => Self {
                    compiler: "php-8.0.3",
                    ..Default::default()
                },
                "fpc-3.2.0" | "fpc" | "pascal" | "pas" => Self {
                    compiler: "fpc-3.2.0",
                    ..Default::default()
                },
                "perl-5.34.0" | "perl" | "pl" => Self {
                    compiler: "perl-5.34.0",
                    ..Default::default()
                },
                "pony-0.39.1" | "pony" => Self {
                    compiler: "pony-0.39.1",
                    ..Default::default()
                },
                // python
                "cpython-3.10.2" | "cpython" | "python" | "py" => Self {
                    compiler: "cpython-3.10.2",
                    ..Default::default()
                },
                "r-4.0.5" | "r" => Self {
                    compiler: "r-4.0.5",
                    ..Default::default()
                },
                // ruby
                "ruby-3.1.0" | "ruby" | "rb" => Self {
                    compiler: "ruby-3.1.0",
                    ..Default::default()
                },
                "rust-1.51.0" | "rust" => Self {
                    compiler: "rust-1.51.0",
                    ..Default::default()
                },
                "sqlite-3.35.5" | "sqlite" | "sql" => Self {
                    compiler: "sqlite-3.35.5",
                    ..Default::default()
                },
                "scala-2.13.5" | "scala" => Self {
                    compiler: "scala-2.13.5",
                    ..Default::default()
                },
                "swift-5.3.3" | "swift" => Self {
                    compiler: "swift-5.3.3",
                    ..Default::default()
                },
                "typescript-4.2.4" | "typescript" | "ts" => Self {
                    compiler: "typescript-4.2.4",
                    ..Default::default()
                },
                "vim-8.2.2811" | "vim" => Self {
                    compiler: "vim-8.2.2811",
                    ..Default::default()
                },
                _ => return Err(Error::Message("do you REALLY need this language?".into())),
            };

            Ok(request)
        }
    }
}

mod repl_python {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r#"
        input = _{ ">>" ~ WHITE_SPACE ~ code }
        code = { ANY* }
    "#]
    pub struct ReplPython;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for ReplPython {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            type Key = <Wandbox as Command>::Key;

            let code = format!(
                r#"
import code
repl = code.InteractiveInterpreter()
input = [{}]
buffer = ""
for line in input:
    buffer += line + "\n"
    if not repl.runsource(buffer):
        buffer = ""
"#,
                parameter
                    .get(&Rule::code)
                    .unwrap()
                    .lines()
                    .map(|line| format!("{line:?}"))
                    .collect::<Vec<_>>()
                    .join(", ")
            );

            Wandbox
                .execute(
                    context,
                    [(Key::lang, "python"), (Key::code, code.as_ref())].into(),
                )
                .await
        }
    }
}

mod geordi {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r#"
        input = _{ ^"geordi" ~ (":" ~ compiler)? ~ (WHITE_SPACE+ ~ argument ~ WHITE_SPACE+ ~ "--")? ~ WHITE_SPACE+ ~ code }
        compiler = { ^"gcc" | ^"clang" }
        argument = { (!(WHITE_SPACE+ ~ "--" ~ WHITE_SPACE) ~ ANY)+ }
        code = _{ ("<<" ~ printing ~ (";" ~ prelude)?) | ("{{" ~ statement ~ "}}" ~ prelude) }
        printing = { (!";" ~ ANY)* }
        statement = { (!"}}" ~ ANY)* }
        prelude = { ANY* }
    "#]
    pub struct Geordi;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for Geordi {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            type Key = <Wandbox as Command>::Key;

            let lang = format!(
                "{}-head",
                parameter
                    .get(&Rule::compiler)
                    .unwrap_or(&"gcc")
                    .to_lowercase()
            );
            let prelude = parameter.get(&Rule::prelude).unwrap_or(&"");
            let input = if let Some(printing) = parameter.get(&Rule::printing) {
                format!(
                    r#"int main() {{ std::cout << {}; std::cout << std::endl; return 0; }}"#,
                    printing
                        .lines()
                        .collect::<Vec<_>>()
                        .join(" << std::endl; std::cout << ")
                )
            } else if let Some(statement) = parameter.get(&Rule::statement) {
                format!(
                    r#"
int main() {{ {{
{}
}} return 0; }}
"#,
                    statement.lines().collect::<Vec<_>>().join("\n")
                )
            } else {
                unreachable!()
            };
            let code = format!("{}{}\n{}\n", GEORDI, prelude, input);

            Wandbox
                .execute(context, {
                    [
                        (Key::lang, lang.as_ref()),
                        (Key::code, code.as_ref()),
                        (Key::opts, "c++2b,cpp-no-pedantic"),
                    ]
                    .into_iter()
                    .chain(
                        parameter
                            .get(&Rule::argument)
                            .map(|argument| [(Key::argument, *argument)])
                            .into_iter()
                            .flatten(),
                    )
                    .collect()
                })
                .await
        }
    }

    const GEORDI: &str = r#"
//#include <bits/stdc++.h>
////////////////////////////////////////////////////////////////////////////////
// C
#ifndef _GLIBCXX_NO_ASSERT
#include <cassert>
#endif
#include <cctype>
#include <cerrno>
#include <cfloat>
#include <ciso646>
#include <climits>
#include <clocale>
#include <cmath>
#include <csetjmp>
#include <csignal>
#include <cstdarg>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <cwchar>
#include <cwctype>

#if __cplusplus >= 201103L
#include <ccomplex>
#include <cfenv>
#include <cinttypes>
//#include <cstdalign>
#include <cstdbool>
#include <cstdint>
#include <ctgmath>
#include <cuchar>
#endif

// C++
#include <algorithm>
#include <bitset>
#include <complex>
#include <deque>
#include <exception>
#include <fstream>
#include <functional>
#include <iomanip>
#include <ios>
#include <iosfwd>
#include <iostream>
#include <istream>
#include <iterator>
#include <limits>
#include <list>
#include <locale>
#include <map>
#include <memory>
#include <new>
#include <numeric>
#include <ostream>
#include <queue>
#include <set>
#include <sstream>
#include <stack>
#include <stdexcept>
#include <streambuf>
#include <string>
#include <typeinfo>
#include <utility>
#include <valarray>
#include <vector>

#if __cplusplus >= 201103L
#include <array>
#include <atomic>
#include <chrono>
#include <codecvt>
#include <condition_variable>
#include <forward_list>
#include <future>
#include <initializer_list>
#include <mutex>
#include <random>
#include <ratio>
#include <regex>
#include <scoped_allocator>
#include <system_error>
#include <thread>
#include <tuple>
#include <typeindex>
#include <type_traits>
#include <unordered_map>
#include <unordered_set>
#endif

#if __cplusplus >= 201402L
#include <shared_mutex>
#endif

#if __cplusplus >= 201703L
#include <any>
#include <charconv>
// #include <execution>
#include <filesystem>
#include <optional>
//#include <memory_resource>
#include <string_view>
#include <variant>
#endif

#if __cplusplus > 201703L
#include <barrier>
#include <bit>
#include <compare>
#include <concepts>
#if __cpp_impl_coroutine
# include <coroutine>
#endif
#include <latch>
#include <numbers>
#include <ranges>
#include <span>
//#include <stop_token>
#include <semaphore>
//#include <source_location>
//#include <syncstream>
#include <version>
#endif
////////////////////////////////////////////////////////////////////////////////
#include <cxxabi.h>
using namespace std;

namespace tracked {
namespace detail {
class Tracked {
protected:
  Tracked();
  Tracked(Tracked const &);
  Tracked(Tracked &&);
  void operator=(Tracked const &);
  void operator=(Tracked &&);
  ~Tracked();
  void set_name(char const *) const;
};
} // namespace detail
struct B : protected detail::Tracked {
  B();
  B(B const &);
  B(B &&);
  B &operator=(B const &);
  B &operator=(B &&);
  virtual ~B();
  void *operator new(std::size_t);
  void *operator new[](std::size_t);
  void *operator new(std::size_t, std::nothrow_t const &) throw();
  void *operator new[](std::size_t, std::nothrow_t const &) throw();
  void *operator new(std::size_t const, void *const p) throw() { return p; }
  void *operator new[](std::size_t const, void *const p) throw() { return p; }
  void operator delete(void *, std::size_t) throw();
  void operator delete[](void *, std::size_t) throw();
  void f() const;
  virtual void vf() const;
  B &operator++();
  B operator++(int);
  void operator*() const;
  friend std::ostream &operator<<(std::ostream &os, const B &);

private:
  void print(std::ostream &) const;
};
struct D : B {
  D();
  D(D const &);
  D(D &&);
  D &operator=(D const &);
  D &operator=(D &&);
  ~D();
  void *operator new(std::size_t);
  void *operator new[](std::size_t);
  void *operator new(std::size_t, std::nothrow_t const &) throw();
  void *operator new[](std::size_t, std::nothrow_t const &) throw();
  void *operator new(std::size_t const, void *const p) throw() { return p; }
  void *operator new[](std::size_t const, void *const p) throw() { return p; }
  void operator delete(void *, std::size_t) throw();
  void operator delete[](void *, std::size_t) throw();
  void operator delete(void *) throw() {}
  void f() const;
  virtual void vf() const;
  friend std::ostream &operator<<(std::ostream &, const D &);

private:
  void print(std::ostream &) const;
};
} // namespace tracked
namespace tracked {
namespace detail {
enum Status { fresh, pillaged, destructed };
struct Entry {
  Tracked const *p;
  char const *name;
  Status status;
};
typedef std::vector<Entry> Entries;
Entries &entries() {
  static Entries *p = new Entries;
  return *p;
}
std::ptrdiff_t id(Entry const &e) { return &e - &entries().front(); }
void print(Entry const &e) { std::printf("%s%lu", e.name, id(e)); }
Entry *entry(Tracked const *const r) {
  for (Entries::reverse_iterator i(entries().rbegin()); i != entries().rend();
       ++i)
    if (i->p == r)
      return &*i;
  return 0;
}
std::ptrdiff_t id(Tracked const &t) { return id(*entry(&t)); }
std::ostream &operator<<(std::ostream &o, Entry const &e) {
  return o << e.name << id(e);
}
void make_entry(Tracked const *const r) {
  if (Entry *const e = entry(r))
    if (e->status != destructed)
      std::cerr << "leaked: " << *e << '.';
  Entry const e = {r, "?", fresh};
  entries().push_back(e);
}
void assert_status_below(Tracked const *const r, Status const st,
                         std::string const &s) {
  Entry *const e = entry(r);
  if (!e)
    std::cerr << "tried to " << s << " non-existent object.";
  if (e->status < st)
    return;
  std::cerr << "tried to " << s
            << (e->status == pillaged ? " pillaged " : " destructed ") << *e
            << '.';
}
void *op_new(std::size_t, bool const array, void *const r,
             char const *const name) {
  if (!r)
    return 0;
  std::cout << "new(" << name << (array ? "[]" : "") << ")";
  std::cout << ' ';
  return r;
}
void op_delete(void *const p, std::size_t const s) {
  ::operator delete(p);
  for (Entries::const_iterator j = entries().begin(); j != entries().end(); ++j)
    if (p <= j->p &&
        static_cast<void const *>(j->p) <= static_cast<char *>(p) + s) {
      std::cout << "delete(" << *j << ")";
      std::cout << ' ';
      return;
    }
}
void op_array_delete(void *const p, std::size_t const s) {
  ::operator delete[](p);
  std::cout << "delete[";
  bool first = true;
  for (Entries::const_iterator j = entries().begin(); j != entries().end(); ++j)
    if (p <= j->p &&
        static_cast<void const *>(j->p) <= static_cast<char *>(p) + s) {
      if (first) {
        first = false;
      } else
        std::cout << ", ";
      std::cout << *j;
    }
  std::cout << ']';
  std::cout << ' ';
}
void Tracked::set_name(char const *const s) const { entry(this)->name = s; }
Tracked::Tracked() { make_entry(this); }
Tracked::Tracked(Tracked const &i) {
  assert_status_below(&i, pillaged, "copy");
  make_entry(this);
}
void Tracked::operator=(Tracked const &r) {
  assert_status_below(this, destructed, "assign to");
  assert_status_below(&r, pillaged, "assign from");
  entry(this)->status = fresh;
}
Tracked::Tracked(Tracked &&r) {
  assert_status_below(&r, pillaged, "move");
  make_entry(this);
  entry(&r)->status = pillaged;
}
void Tracked::operator=(Tracked &&r) {
  assert_status_below(this, destructed, "move-assign to");
  assert_status_below(&r, pillaged, "move");
  entry(this)->status = fresh;
  entry(&r)->status = pillaged;
}
Tracked::~Tracked() {
  assert_status_below(this, destructed, "re-destruct");
  entry(this)->status = destructed;
}
} // namespace detail
B::B() {
  set_name("B");
  print(std::cout);
  std::cout << '*';
  std::cout << ' ';
}
B::B(B const &b) : Tracked(b) {
  set_name("B");
  print(std::cout);
  std::cout << "*(";
  b.print(std::cout);
  std::cout << ')';
  std::cout << ' ';
}
B &B::operator=(B const &b) {
  Tracked::operator=(b);
  print(std::cout);
  std::cout << '=';
  b.print(std::cout);
  std::cout << ' ';
  return *this;
}
B::~B() {
  assert_status_below(this, detail::destructed, "destruct");
  print(std::cout);
  std::cout << '~';
  std::cout << ' ';
}
void *B::operator new(std::size_t const s) {
  return detail::op_new(s, false, ::operator new(s), "B");
}
void *B::operator new[](std::size_t const s) {
  return detail::op_new(s, true, ::operator new[](s), "B");
}
void *B::operator new(std::size_t const s, std::nothrow_t const &t) throw() {
  return detail::op_new(s, false, ::operator new(s, t), "B");
}
void *B::operator new[](std::size_t const s, std::nothrow_t const &t) throw() {
  return detail::op_new(s, true, ::operator new[](s, t), "B");
}
void B::operator delete(void *const p, std::size_t const s) throw() {
  detail::op_delete(p, s);
}
void B::operator delete[](void *const p, std::size_t const s) throw() {
  detail::op_array_delete(p, s);
}
void B::f() const {
  assert_status_below(this, detail::pillaged, "call B::f() on");
  print(std::cout);
  std::cout << ".f()";
  std::cout << ' ';
}
void B::vf() const {
  assert_status_below(this, detail::pillaged, "call B::vf() on");
  print(std::cout);
  std::cout << ".vf()";
  std::cout << ' ';
}
B::B(B &&b) : Tracked(std::move(b)) {
  set_name("B");
  b.print(std::cout);
  std::cout << "=>";
  print(std::cout);
  std::cout << '*';
  std::cout << ' ';
}
B &B::operator=(B &&b) {
  Tracked::operator=(std::move(b));
  b.print(std::cout);
  std::cout << "=>";
  print(std::cout);
  std::cout << ' ';
  return *this;
}
B &B::operator++() {
  assert_status_below(this, detail::pillaged, "pre-increment");
  std::cout << "++";
  print(std::cout);
  std::cout << ' ';
  return *this;
}
B B::operator++(int) {
  assert_status_below(this, detail::pillaged, "post-increment");
  B const r(*this);
  operator++();
  return r;
}
void B::operator*() const {
  assert_status_below(this, detail::pillaged, "dereference");
  std::cout << '*';
  print(std::cout);
  std::cout << ' ';
}
void B::print(std::ostream &o) const { o << 'B' << id(*this); }
std::ostream &operator<<(std::ostream &o, B const &b) {
  assert_status_below(&b, detail::pillaged, "read");
  b.print(o);
  return o;
}
D::D() {
  set_name("D");
  print(std::cout);
  std::cout << '*';
  std::cout << ' ';
}
D::D(D const &d) : B(d) {
  set_name("D");
  print(std::cout);
  std::cout << "*(";
  d.print(std::cout);
  std::cout << ')';
  std::cout << ' ';
}
D &D::operator=(D const &d) {
  B::operator=(d);
  print(std::cout);
  std::cout << '=';
  d.print(std::cout);
  std::cout << ' ';
  return *this;
}
D::~D() {
  assert_status_below(this, detail::destructed, "destruct");
  print(std::cout);
  std::cout << '~';
  std::cout << ' ';
}
void *D::operator new(std::size_t const s) {
  return detail::op_new(s, false, ::operator new(s), "D");
}
void *D::operator new[](std::size_t const s) {
  return detail::op_new(s, true, ::operator new[](s), "D");
}
void *D::operator new(std::size_t const s, std::nothrow_t const &t) throw() {
  return detail::op_new(s, false, ::operator new(s, t), "D");
}
void *D::operator new[](std::size_t const s, std::nothrow_t const &t) throw() {
  return detail::op_new(s, true, ::operator new[](s, t), "D");
}
void D::operator delete(void *const p, std::size_t const s) throw() {
  detail::op_delete(p, s);
}
void D::operator delete[](void *const p, std::size_t const s) throw() {
  detail::op_array_delete(p, s);
}
void D::f() const {
  assert_status_below(this, detail::pillaged, "call D::f() on");
  print(std::cout);
  std::cout << ".f()";
  std::cout << ' ';
}
void D::vf() const {
  assert_status_below(this, detail::pillaged, "call D::vf() on");
  print(std::cout);
  std::cout << ".vf()";
  std::cout << ' ';
}
void D::print(std::ostream &o) const { o << 'D' << id(*this); }
std::ostream &operator<<(std::ostream &o, D const &d) {
  assert_status_below(&d, detail::pillaged, "read");
  d.print(o);
  std::cout << ' ';
  return o;
}
D::D(D &&d) : B(std::move(d)) {
  set_name("D");
  d.print(std::cout);
  std::cout << "=>";
  print(std::cout);
  std::cout << '*';
  std::cout << ' ';
}
D &D::operator=(D &&d) {
  B::operator=(std::move(d));
  d.print(std::cout);
  std::cout << ' ';
  std::cout << "=>";
  print(std::cout);
  std::cout << ' ';
  return *this;
}
void atexit() {
  bool first = true;
  for (detail::Entries::const_iterator i = detail::entries().begin();
       i != detail::entries().end(); ++i)
    if (i->status != detail::destructed) {
      if (first) {
        std::printf("leaked: ");
        first = false;
      } else {
        std::printf(", ");
      }
      print(*i);
    }
  if (!first) {
    std::printf(".");
    abort();
  }
}
} // namespace tracked
"#;
}

mod rust {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r#"
        input = _{ ^"rust" ~ WHITE_SPACE+ ~ code }
        code = { ANY* }
    "#]
    pub struct Rust;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for Rust {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let request = Request {
                backtrace: false,
                channel: "nightly",
                code: parameter.get(&Rule::code).unwrap(),
                crate_type: "bin",
                edition: "2021",
                mode: "debug",
                tests: false,
            };

            let text = reqwest::Client::new()
                .post("https://play.rust-lang.org/execute")
                .json(&request)
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;

            let response = serde_json::from_str(&text).context(format!("json error: {text}"))?;

            match response {
                Response {
                    success: true,
                    #[allow(unused_variables)]
                        stderr: _,
                    stdout,
                } if stdout.is_empty() => context.send_fmt("no output").await,
                Response {
                    success: true,
                    #[allow(unused_variables)]
                        stderr: _,
                    stdout,
                } => context.send_fmt(stdout).await,
                Response {
                    success: false,
                    stderr,
                    #[allow(unused_variables)]
                        stdout: _,
                } => {
                    context
                        .send_fmt([
                            MessageText {
                                color: (Some(Color::Red), None),
                                text: "error:".into(),
                                ..Default::default()
                            },
                            " ".into(),
                            stderr.into(),
                        ])
                        .await
                }
            }
        }
    }

    #[allow(dead_code)]
    #[derive(Debug, Default, Serialize)]
    struct Request<'a> {
        backtrace: bool,
        channel: &'a str,
        code: &'a str,
        #[serde(rename = "crateType")]
        crate_type: &'a str,
        edition: &'a str,
        mode: &'a str,
        tests: bool,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Response<'a> {
        success: bool,
        #[serde(borrow)]
        stdout: Cow<'a, str>,
        #[serde(borrow)]
        stderr: Cow<'a, str>,
    }
}

mod repl_rust {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r#"
        input = _{ "||" ~ WHITE_SPACE+ ~ code }
        code = { ANY* }
    "#]
    pub struct ReplRust;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for ReplRust {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            type Key = <Rust as Command>::Key;

            let code = format!(
                r#"
#![allow(warnings)]
#![feature(core_intrinsics, stmt_expr_attributes)]
fn main() {{ println!("{{:?}}", {{
{}
}}); }}
"#,
                parameter.get(&Rule::code).unwrap()
            );

            Rust.execute(context, [(Key::code, code.as_ref())].into())
                .await
        }
    }
}

mod go {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r#"
        input = _{ ^"go" ~ WHITE_SPACE+ ~ code }
        code = { ANY* }
    "#]
    pub struct Go;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for Go {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let text = reqwest::Client::new()
                .post("https://go.dev/_/compile")
                .form(&[
                    ("version", "2"),
                    ("body", parameter.get(&Rule::code).unwrap()),
                    ("withVet", "true"),
                ])
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;

            let response = serde_json::from_str(&text).context(format!("json error: {text}"))?;

            match response {
                Response {
                    errors,
                    events: None,
                } if errors.is_empty() => context.send_fmt("no output").await,
                Response {
                    errors,
                    events: Some(events),
                } if errors.is_empty() => {
                    context
                        .send_itr(events.into_iter().filter_map(|event| {
                            if event.kind == "stdout" {
                                Some(event.message.to_owned())
                            } else {
                                None
                            }
                        }))
                        .await
                }
                Response {
                    errors,
                    #[allow(unused_variables)]
                        events: _,
                } => {
                    context
                        .send_fmt([
                            MessageText {
                                color: (Some(Color::Red), None),
                                text: "error:".into(),
                                ..Default::default()
                            },
                            " ".into(),
                            errors.into(),
                        ])
                        .await
                }
            }
        }
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Response<'a> {
        #[serde(borrow)]
        #[serde(rename = "Errors")]
        errors: Cow<'a, str>,
        #[serde(borrow)]
        #[serde(rename = "Events")]
        events: Option<Vec<Event<'a>>>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Event<'a> {
        #[serde(borrow)]
        #[serde(rename = "Message")]
        message: Cow<'a, str>,
        #[serde(rename = "Kind")]
        kind: &'a str,
        #[serde(rename = "Delay")]
        delay: u64,
    }
}
