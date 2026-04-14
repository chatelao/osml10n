/* 

Unaccent UTF-8 string for latin characters only using libutf8proc

(c) 2026 Sven Geggus <sven@geggus.net>

*/

#include <stdlib.h>
#include <string.h>
#include <utf8proc.h>

#include <lua.h>
#include <lauxlib.h>
#include <lualib.h>

/* 
   Checks if a codepoint is a latin character.
   after doing NFD we have e.g, "é" → "e" + U+0301,
   which means base characters are usually in ASCII Latin range
*/
static int is_latin(utf8proc_int32_t cp) {
  return (cp >= 0x0041 && cp <= 0x005A) ||  /* A-Z              */
         (cp >= 0x0061 && cp <= 0x007A) ||  /* a-z              */
         (cp >= 0x00C0 && cp <= 0x00D6) ||  /* Latin-1 Suppl.   */
         (cp >= 0x00D8 && cp <= 0x00F6) ||  /* (without × ÷)    */
         (cp >= 0x00F8 && cp <= 0x00FF) ||
         (cp >= 0x0100 && cp <= 0x017F) ||  /* Latin Extended-A  */
         (cp >= 0x0180 && cp <= 0x024F) ||  /* Latin Extended-B  */
         (cp >= 0x0250 && cp <= 0x02AF) ||  /* IPA Extensions    */
         (cp >= 0x1D00 && cp <= 0x1DBF) ||  /* Phonetic Ext.     */
         (cp >= 0x1E00 && cp <= 0x1EFF) ||  /* Latin Ext. Add.   */
         (cp >= 0x2C60 && cp <= 0x2C7F) ||  /* Latin Extended-C  */
         (cp >= 0xA720 && cp <= 0xA7FF) ||  /* Latin Extended-D  */
         (cp >= 0xAB30 && cp <= 0xAB6F) ||  /* Latin Extended-E  */
         (cp >= 0xFB00 && cp <= 0xFB06);    /* Latin-Ligatures   */
}

static int is_combining_mark(utf8proc_int32_t cp) {
  utf8proc_category_t cat = utf8proc_category(cp);
  return cat == UTF8PROC_CATEGORY_MN ||  /* Mark, Nonspacing         */
         cat == UTF8PROC_CATEGORY_MC ||  /* Mark, Spacing Combining  */
         cat == UTF8PROC_CATEGORY_ME;    /* Mark, Enclosing          */
}

char *unaccent(const char *input) {
  /* step 1: Decompose without STRIPMARK */
  utf8proc_uint8_t *decomposed = NULL;
  utf8proc_option_t options = UTF8PROC_COMPAT | UTF8PROC_DECOMPOSE;

  utf8proc_ssize_t dec_len = utf8proc_map(
      (const utf8proc_uint8_t *)input,
      (utf8proc_ssize_t)strlen(input),
      &decomposed,
      options
  );

  if (dec_len < 0) {
    fprintf(stderr, "utf8proc error: %s\n", utf8proc_errmsg(dec_len));
    return NULL;
  }

  /* step 2: remove combining marks only after latin base characters */
  utf8proc_uint8_t *output = malloc((size_t)dec_len + 1);
  if (!output) { free(decomposed); return NULL; }

  utf8proc_ssize_t i = 0;
  utf8proc_ssize_t out_pos = 0;
  int last_base_is_latin = 0;

  while (i < dec_len) {
    utf8proc_int32_t cp;
    utf8proc_ssize_t bytes = utf8proc_iterate(
      decomposed + i, dec_len - i, &cp
    );
    if (bytes < 0) break;

    if (is_combining_mark(cp)) {
      if (!last_base_is_latin) {
        /* non-latin, copy mark */
        memcpy(output + out_pos, decomposed + i, (size_t)bytes);
        out_pos += bytes;
      }
        /* latin, do not copy mark */
    } else {
      /* always copy base mark */
      last_base_is_latin = is_latin(cp);
      memcpy(output + out_pos, decomposed + i, (size_t)bytes);
      out_pos += bytes;
    }
    i += bytes;
  }
  
  output[out_pos] = '\0';
  free(decomposed);
  return (char *)realloc(output, (size_t)out_pos + 1);
}

static int unac4lua(lua_State *L) {
  char *result = NULL;
  const char *input = lua_tostring(L, 1);

  result = unaccent(input);

  if (result == NULL) {
    lua_pushnil(L);
  } else {
    lua_pushstring(L, (char *)result);
  }
  // assuming utf8proc_map will allocate memory
  free(result);
  return 1;
}

/* library to be registered */
static const struct luaL_Reg lib_unaccent [] = {
  {"unaccent", unac4lua},
  {NULL, NULL}
};

/* name of this function must be exactly called like this */
int luaopen_unaccent (lua_State *L){
    luaL_newlib(L, lib_unaccent);
    return 1;
}
